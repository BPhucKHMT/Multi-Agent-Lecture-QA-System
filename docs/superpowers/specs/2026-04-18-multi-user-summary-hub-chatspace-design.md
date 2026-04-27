# Multi-user Frontend (Summary Hub + Chatspace) Design

**Mục tiêu:** Mở rộng frontend hiện tại để hỗ trợ nhiều người dùng song song theo user context tách biệt, đồng thời giữ kiến trúc sẵn sàng cắm backend auth DB + Redis trong phase sau mà không phải đập lại UI flow.

**Phạm vi:** Frontend behavior + contract chuẩn hóa giữa frontend và backend cho Summary Hub và Chatspace. Không triển khai auth thật, không thay đổi core logic RAG/Supervisor.

---

## 1) Context và ràng buộc hệ thống

- Dự án có 2 không gian:
  1. **Summary Hub**: dashboard tĩnh, gọi pipeline tóm tắt độc lập.
  2. **Chatspace**: hội thoại động do Supervisor điều phối.
- Backend hiện tại vẫn dựa nhiều vào in-memory cho hội thoại.
- Yêu cầu mở rộng hiện tại:
  - Hỗ trợ nhiều user ở frontend ngay bây giờ.
  - Chưa làm login thật; backend DB login + Redis để phase sau.
  - Summary phải hiển thị riêng theo từng user.
  - Mục tiêu tải ban đầu ~50 users đồng thời.

---

## 2) Các phương án đã cân nhắc

### A. Frontend-only isolation
- Chỉ tách dữ liệu ở client, không chuẩn hóa contract user context.
- Ưu điểm: nhanh nhất.
- Nhược điểm: khó nâng cấp về sau, nguy cơ lệch behavior khi cắm auth/redis.

### B. Hybrid-ready (**được chọn**)
- Frontend dùng user context chuẩn hóa ngay từ đầu.
- API request đính user context cho cả Summary Hub và Chatspace.
- Backend hiện tại chưa auth thật vẫn chạy được; phase sau chỉ thay nguồn định danh.
- Ưu điểm: cân bằng tốt giữa tốc độ và khả năng mở rộng.

### C. Auth-first ngay bây giờ
- Dựng login luồng đầy đủ từ đầu.
- Ưu điểm: chặt chẽ hơn.
- Nhược điểm: scope lớn, chậm rollout, phụ thuộc backend lớn.

---

## 3) Thiết kế kiến trúc được chọn

## 3.1 User Context chuẩn hóa

Frontend tạo và quản lý `user_context`:

```ts
type UserContext = {
  anonymous_user_id: string;
  device_id: string;
};
```

Nguyên tắc:
- Sinh một lần khi app khởi chạy nếu localStorage chưa có.
- Dùng chung cho mọi request từ Summary Hub và Chatspace.
- Là nền tảng tạm thời trước khi có auth thật.

## 3.2 Frontend layers

1. **Identity Layer**
   - `IdentityProvider` cấp `user_context` cho toàn app.
2. **Feature Layer**
   - `SummaryHubPage`, `ChatPage` dùng chung user context.
3. **Data Layer**
   - API client tự động đính `user_context`.
4. **State Layer**
   - Namespace state theo user để chặn trộn dữ liệu.

## 3.3 Tương thích tương lai (Auth + Redis)

Khi backend auth/login hoàn thiện:
- Thay nguồn `anonymous_user_id` bằng `authenticated_user_id`.
- Giữ nguyên phần lớn flow request, key builder, và screen behavior.
- Không cần viết lại luồng chuyển Summary Hub -> Chatspace.

---

## 4) Data flow end-to-end

## 4.1 App bootstrap
1. App start.
2. Đọc localStorage:
   - Nếu chưa có -> tạo `anonymous_user_id`, `device_id`.
3. Mount `IdentityProvider`.

## 4.2 Summary Hub flow
1. User chọn video, bấm tóm tắt.
2. Frontend gọi `/summarize` với `video_id` + `user_context`.
3. Render kết quả trong namespace riêng của user hiện tại.
4. Không hiển thị kết quả từ user khác.

## 4.3 Summary Hub -> Chatspace flow
1. User bấm “Thảo luận về video này”.
2. Frontend điều hướng sang Chatspace.
3. Inject ngữ cảnh video vào chat context.
4. Giữ nguyên cùng `user_context`.

## 4.4 Chatspace flow
1. Gửi `/chat` hoặc `/chat/stream` với:
   - `conversation_id`
   - `messages`
   - `user_message`
   - `user_context`
2. Render response + citation như contract hiện tại.
3. State/cache theo namespace user + conversation.

---

## 5) Data model và namespace đề xuất (frontend)

```ts
type SummaryKey = `summary:${string}:${string}`; // summary:{user_id}:{video_id}
type ChatKey = `chat:${string}:${string}`; // chat:{user_id}:{conversation_id}
```

Nguyên tắc:
- Mọi local cache/store key có prefix theo user.
- Clear/rebuild context thì reset namespace tương ứng.

---

## 6) Contract đề xuất để backend-ready

Không phá vỡ payload cũ, chỉ mở rộng chuẩn hóa:

1. Header-based (ưu tiên):
   - `X-Anonymous-User-Id`
   - `X-Device-Id`
2. Hoặc payload field `user_context` nếu endpoint cần.

Giai đoạn hiện tại có thể cho backend bỏ qua field mới, nhưng frontend luôn gửi nhất quán để chuẩn bị phase sau.

---

## 7) Error handling và an toàn behavior

1. **Missing user context**
   - Tự tạo context mới.
   - Reset cache namespace cũ.
2. **Network/timeout**
   - Giữ optimistic message.
   - Retry với cùng payload + cùng context.
3. **Response/context mismatch**
   - UI không render dữ liệu chéo user (fail-closed ở UI).
4. **Cross-page consistency**
   - Nếu context đổi giữa Summary Hub và Chatspace, hủy chuyển ngữ cảnh và yêu cầu tải lại.

---

## 8) Kiểm thử

## 8.1 Unit tests
- Sinh/đọc `user_context` từ localStorage.
- Key builder theo namespace.
- Validator chống context mismatch.

## 8.2 Integration tests
- Hai user context đồng thời trên cùng backend không leak dữ liệu summary/chat.
- Flow Summary Hub -> Chatspace giữ nguyên video context + user context.
- Retry flow không đổi context.

## 8.3 Smoke tests
- Mô phỏng ~50 users với user contexts khác nhau.
- Kiểm tra không có hiển thị chéo trong UI state.

---

## 9) Non-goals của phase này

- Chưa làm login/logout thật.
- Chưa có RBAC/workspace multi-tenant.
- Chưa có cross-device sync.

---

## 10) Acceptance criteria

1. Summary Hub và Chatspace đều chạy trên cùng user context tạm thời.
2. Không có rò rỉ hiển thị summary/chat giữa hai user contexts khác nhau.
3. Luồng chuyển Summary Hub -> Chatspace giữ được ngữ cảnh video.
4. Frontend giữ tương thích với backend hiện tại, đồng thời sẵn sàng cắm auth DB + Redis về sau.
