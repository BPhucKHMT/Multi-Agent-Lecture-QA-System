# Backend Implementation Plan (FastAPI + Redis + JWT + PostgreSQL)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây dựng backend production-ready cho hệ thống hỏi đáp, có xác thực JWT an toàn, lưu trữ người dùng bền vững, cache/session control bằng Redis, và API rõ ràng cho frontend.

**Architecture:** Sử dụng FastAPI theo mô hình module hóa theo domain (`auth`, `users`, `chat`, `admin`), PostgreSQL làm nguồn dữ liệu chính (nguồn sự thật), Redis làm lớp tốc độ cao cho token/session/rate-limit/cache ngắn hạn. JWT theo chiến lược access token ngắn hạn + refresh token xoay vòng (rotation) + revoke list trên Redis để kiểm soát đăng xuất và phát hiện reuse.

**Tech Stack:** FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL, Redis, Pydantic v2, PyJWT/python-jose, passlib[bcrypt]/argon2, pytest.

---

## 1) Scope và nguyên tắc

### In scope
- Auth: đăng ký, đăng nhập, refresh token, logout 1 thiết bị, logout all.
- User management: lấy profile, cập nhật profile cơ bản, đổi mật khẩu.
- Session management: theo dõi phiên đăng nhập theo thiết bị.
- Security baseline: hashing mạnh, JWT rotation, revoke, rate limit, audit log tối thiểu.
- API contract rõ cho frontend và mở rộng sau này.

### Out of scope (giai đoạn này)
- OAuth social login (Google/GitHub), SSO.
- RBAC phức tạp đa vai trò (chỉ `user` và `admin` baseline).
- Microservices.

### Non-functional target
- Response auth endpoints < 300ms p95 (không tính network ngoài).
- Token compromise blast radius thấp nhờ access token ngắn hạn.
- Có khả năng scale ngang backend stateless.

---

## 2) Đề xuất 3 phương án và quyết định

### Phương án A (Khuyến nghị): PostgreSQL + Redis + JWT rotation
- **Ưu điểm:** cân bằng tốt giữa an toàn, hiệu năng, khả năng truy vấn người dùng, và mở rộng.
- **Nhược điểm:** complexity cao hơn stateless JWT thuần.

### Phương án B: PostgreSQL + JWT stateless thuần (không Redis)
- **Ưu điểm:** triển khai nhanh.
- **Nhược điểm:** khó revoke token tức thì, logout all không mạnh, bảo mật kém hơn khi token lộ.

### Phương án C: MongoDB + Redis + JWT
- **Ưu điểm:** linh hoạt schema.
- **Nhược điểm:** bài toán user/auth phù hợp quan hệ + ràng buộc của SQL hơn; migration/reporting khó hơn.

**Quyết định:** Chọn **Phương án A**.

---

## 3) Kiến trúc tổng thể backend

```text
Client (Web/App)
   -> FastAPI (REST)
      -> Auth Service
      -> User Service
      -> Chat Service (tích hợp RAG hiện có)
      -> Admin Service
   -> PostgreSQL (users, sessions, audit, refresh_token_families)
   -> Redis (revoked_jti, rate_limit, cache, active_session_flags)
```

### Phân lớp mã nguồn đề xuất
```text
backend/
├── app/
│   ├── main.py
│   ├── core/              # config, security utils, constants
│   ├── db/                # session, models, migrations hook
│   ├── modules/
│   │   ├── auth/
│   │   ├── users/
│   │   ├── chat/
│   │   └── admin/
│   ├── schemas/           # request/response pydantic
│   ├── repositories/      # db access
│   ├── services/          # business logic
│   └── api/               # routers, dependencies
└── tests/
```

---

## 4) Thiết kế dữ liệu (DB lưu người dùng như thế nào)

## 4.1 PostgreSQL tables

### `users`
- `id` (uuid, pk)
- `email` (varchar, unique, indexed, lowercase canonical)
- `username` (varchar, unique, indexed)
- `password_hash` (varchar)
- `role` (`user` | `admin`)
- `is_active` (bool, default true)
- `is_verified` (bool, default false)
- `last_login_at` (timestamp nullable)
- `created_at`, `updated_at`

### `user_profiles`
- `user_id` (uuid, pk/fk users.id)
- `full_name` (varchar nullable)
- `avatar_url` (varchar nullable)
- `bio` (text nullable)
- `updated_at`

### `user_sessions`
- `id` (uuid, pk)
- `user_id` (fk)
- `device_id` (varchar, indexed)
- `user_agent` (varchar)
- `ip_address` (varchar)
- `refresh_token_hash` (varchar)  <!-- chỉ lưu hash -->
- `token_family_id` (uuid)        <!-- quản lý rotation family -->
- `expires_at` (timestamp)
- `revoked_at` (timestamp nullable)
- `created_at`, `updated_at`

### `audit_logs`
- `id` (bigserial pk)
- `user_id` (uuid nullable)
- `action` (varchar, indexed)  // login_success, login_fail, refresh_reuse_detected...
- `metadata` (jsonb)
- `created_at` (timestamp indexed)

### Chỉ mục quan trọng
- `users(email)`, `users(username)` unique index.
- `user_sessions(user_id, revoked_at)`.
- `audit_logs(action, created_at)`.

## 4.2 Redis keys

- `auth:revoked_jti:{jti}` = `1` (TTL tới khi token hết hạn).
- `auth:rate_limit:login:{ip}` (counter + window).
- `auth:rate_limit:register:{ip}`.
- `auth:active_session:{session_id}` = lightweight flag.
- `cache:user_profile:{user_id}` (TTL ngắn, ví dụ 5 phút).

**Nguyên tắc:** Redis chỉ là lớp tăng tốc/kiểm soát tạm thời; dữ liệu nguồn vẫn ở PostgreSQL.

---

## 5) JWT strategy chi tiết

## 5.1 Token model
- **Access token**: TTL ngắn (10-15 phút), chứa `sub`, `role`, `jti`, `iat`, `exp`, `type=access`.
- **Refresh token**: TTL dài hơn (7-30 ngày), chứa `sub`, `sid`, `jti`, `family_id`, `type=refresh`.

## 5.2 Rotation + reuse detection
1. Login tạo cặp access/refresh ban đầu + session record.
2. Khi refresh:
   - Verify refresh token.
   - So khớp hash với session hiện tại.
   - Nếu hợp lệ: phát hành refresh token mới, cập nhật hash mới (rotation).
   - Revoke token cũ (Redis + DB timestamp).
3. Nếu phát hiện token cũ bị reuse:
   - Revoke toàn bộ `token_family_id`.
   - Buộc user đăng nhập lại.
   - Ghi audit log mức cảnh báo.

## 5.3 Logout
- **Logout thiết bị hiện tại:** revoke refresh token phiên hiện tại + ghi `revoked_jti` cho access hiện tại.
- **Logout all devices:** revoke tất cả sessions user.

---

## 6) Danh sách API chi tiết

## 6.1 Auth APIs

### `POST /api/v1/auth/register`
- **Body:** `email`, `username`, `password`
- **200/201:** user basic info
- **409:** email/username đã tồn tại
- **422:** validation lỗi

### `POST /api/v1/auth/login`
- **Body:** `email_or_username`, `password`, `device_id`
- **200:** `access_token`, `refresh_token`, `expires_in`, `token_type`
- **401:** sai thông tin đăng nhập
- **429:** vượt rate limit

### `POST /api/v1/auth/refresh`
- **Body:** `refresh_token`
- **200:** token pair mới
- **401:** refresh token invalid/expired/reused

### `POST /api/v1/auth/logout`
- **Auth:** Bearer access
- **Body:** `refresh_token` (tuỳ chọn nhưng khuyến nghị bắt buộc)
- **204:** success

### `POST /api/v1/auth/logout-all`
- **Auth:** Bearer access
- **204:** success

### `GET /api/v1/auth/sessions`
- **Auth:** Bearer access
- **200:** list sessions (thiết bị, last_seen, trạng thái)

### `DELETE /api/v1/auth/sessions/{session_id}`
- **Auth:** Bearer access
- **204:** revoke 1 session cụ thể

## 6.2 User APIs

### `GET /api/v1/users/me`
- **Auth:** required
- **200:** profile hiện tại

### `PATCH /api/v1/users/me`
- **Auth:** required
- **Body:** `full_name`, `avatar_url`, `bio` (partial)
- **200:** profile đã cập nhật

### `POST /api/v1/users/me/change-password`
- **Auth:** required
- **Body:** `current_password`, `new_password`
- **204:** success (và revoke các session khác nếu policy yêu cầu)

## 6.3 Chat bridge APIs (nếu backend này làm gateway cho RAG)

### `POST /api/v1/chat`
- **Auth:** required (tuỳ policy; có thể cho guest qua key riêng)
- Forward sang luồng RAG hiện có, thêm `user_id` để audit/rate-limit.

### `POST /api/v1/chat/stream`
- Stream response + giữ trace id để debug.

## 6.4 Admin APIs (baseline)

### `GET /api/v1/admin/users`
- **Auth:** admin
- Filter theo `is_active`, `created_at`.

### `PATCH /api/v1/admin/users/{user_id}/status`
- **Auth:** admin
- Enable/disable user.

---

## 7) Security controls bắt buộc

- Password hash: Argon2 hoặc bcrypt cost phù hợp.
- JWT secret/keys quản lý qua env + rotation policy.
- HTTPS bắt buộc ở production.
- CORS whitelist theo domain thật.
- Rate limit cho login/register/refresh.
- Anti-bruteforce: lock tạm thời sau N lần fail.
- Chuẩn hóa lỗi auth: không leak thông tin ("invalid credentials" chung).
- Audit log cho hành động nhạy cảm.

---

## 8) Kế hoạch triển khai theo phase

### Phase 1: Foundation
- [ ] Khởi tạo cấu trúc backend FastAPI module hóa.
- [ ] Setup config/env + DB session + Redis client.
- [ ] Setup Alembic migration baseline.

### Phase 2: Auth core
- [ ] Tạo bảng users, profiles, sessions, audit_logs.
- [ ] Register/login với password hashing.
- [ ] Access + refresh token phát hành chuẩn claim.

### Phase 3: Session & token hardening
- [ ] Refresh rotation + reuse detection.
- [ ] Logout, logout-all, list/revoke sessions.
- [ ] Revoke list trong Redis + policy cleanup.

### Phase 4: User profile & password lifecycle
- [ ] `/users/me`, update profile.
- [ ] Change password + policy revoke session liên quan.

### Phase 5: Chat integration & guardrails
- [ ] Gắn middleware auth/rate-limit cho chat endpoints.
- [ ] Trace id + audit cho truy vấn chat.

### Phase 6: Observability + release hardening
- [ ] Structured logs, health checks, readiness checks.
- [ ] Backup/migration rollback strategy.
- [ ] Security review + load smoke test.

---

## 9) Kế hoạch test

## 9.1 Unit tests
- Hash/verify password.
- JWT create/verify + expired + wrong type.
- Refresh rotation logic và reuse detection.

## 9.2 Integration tests
- Register -> login -> refresh -> logout flow.
- Logout all revoke đúng tất cả sessions.
- Rate-limit trả đúng 429 trong cửa sổ giới hạn.

## 9.3 Security tests (targeted)
- Refresh token reuse attack simulation.
- Privilege escalation check (user gọi admin API).
- Token tampering (signature invalid).

---

## 10) Rủi ro chính và giảm thiểu

1. **Rò rỉ refresh token phía client**
   - Giảm thiểu: rotation + reuse detection + family revoke.
2. **Redis down**
   - Giảm thiểu: degrade có kiểm soát (chặn refresh tạm), alert sớm.
3. **Migration lỗi khi release**
   - Giảm thiểu: migration backward-compatible, dry-run staging, backup.
4. **Tắc nghẽn login peak**
   - Giảm thiểu: index chuẩn, rate-limit, cache policy hợp lý.

---

## 11) Checklist review plan (đã tự review kỹ)

### 11.1 Coverage review
- [x] Có kiến trúc tổng thể.
- [x] Có quyết định stack (FastAPI + Redis + JWT + PostgreSQL).
- [x] Có mô hình dữ liệu lưu người dùng và session.
- [x] Có danh sách API cụ thể kèm mã lỗi chính.
- [x] Có security controls.
- [x] Có roadmap theo phase + test strategy + risk handling.

### 11.2 Placeholder scan
- [x] Không để `TODO/TBD`.
- [x] Không có mục mô tả mơ hồ kiểu "handle sau".

### 11.3 Consistency scan
- [x] Thuật ngữ token/session/family dùng nhất quán.
- [x] Redis dùng cho revoke/rate-limit/cache nhất quán với kiến trúc.
- [x] API auth bám theo strategy JWT rotation.

### 11.4 Scope sanity check
- [x] Scope đủ chi tiết để implement.
- [x] Không mở rộng sang OAuth/microservices để tránh over-scope.

---

## 12) Quyết định mặc định đã chốt (do thiếu phản hồi thời gian thực)

- Chọn PostgreSQL thay MongoDB/MySQL cho auth/user domain.
- Chọn JWT access ngắn hạn + refresh rotation.
- Chọn Redis cho revoke/rate-limit/session flag.

Khi cần thay đổi các default này, cập nhật lại tài liệu trước khi bắt đầu code để tránh lệch kiến trúc.

---

## 13) Ý tưởng mở rộng cho tương lai (Future Ideas)

Dưới đây là các hướng phát triển để nâng cấp hệ thống từ một bản mẫu (MVP) lên thành một sản phẩm hoàn thiện chuyên nghiệp:

### 13.1 Lưu trữ lịch sử hội thoại vĩnh viễn (Conversation Persistence)
- **Mục tiêu**: Thay vì chỉ lưu tin nhắn trong bộ nhớ tạm (React State), chúng ta sẽ lưu chúng vào PostgreSQL hoặc MongoDB.
- **Giá trị**: Người dùng có thể quay lại xem các câu hỏi cũ, bản tóm tắt cũ và tiếp tục thảo luận bất cứ lúc nào, trên bất kỳ thiết bị nào.



### 13.4 Bảng điều khiển quản trị dữ liệu (Ingestion Admin Panel)
- **Mục tiêu**: Xây dựng UI cho phép Admin dán link YouTube Playlist, theo dõi tiến độ Crawl/Embed và quản lý các chunk dữ liệu.
- **Giá trị**: Loại bỏ việc phải chạy script thủ công qua Terminal, giúp người không chuyên cũng có thể cập nhật kiến thức cho hệ thống.

### 13.5 Cấu hình Redis Persistence
- **Mục tiêu**: Chuyển đổi Redis từ cache thuần túy sang lưu trữ bền vững (bật AOF/RDB).
- **Giá trị**: Đảm bảo các thông tin về Rate Limit, Session và các bản tóm tắt đã cache không bị mất khi server bảo trì hoặc reset.

