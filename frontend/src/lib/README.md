# lib — API Clients & Utilities

`frontend/src/lib/` chứa logic không trực tiếp là UI: API client, parser, formatter và helper dùng chung.

---

## Cấu trúc

```txt
lib/
├── api/    # Hàm gọi backend API
└── utils/  # Helper format/parse/citation/etc.
```

---

## API layer

API layer là nơi duy nhất nên biết chi tiết endpoint backend:

```txt
React page/component
  ↓
lib/api function
  ↓
fetch/EventSource/stream parser
  ↓
FastAPI backend
```

Chat streaming cần parse SSE event:

- `status`;
- `token`;
- `context`;
- `metadata`;
- `error`;
- `[DONE]`.

### Làm mới phiên đăng nhập

`client.ts` cung cấp `authenticatedFetch` dùng chung cho API JSON và `streamChat`.
Khi nhận HTTP 401, client gửi `POST /api/v1/auth/refresh` với
`{ "refresh_token": "..." }`, lưu cả `access_token` và `refresh_token` mới vào
localStorage, rồi thử lại request gốc tối đa một lần. Các request đồng thời trong
cùng trang dùng chung một refresh đang chạy; 401 đến muộn dùng token đã xoay
thay vì xoay lại. Login, register và refresh không được tự động thử lại.

Nếu thiếu refresh token, endpoint refresh từ chối phiên bằng HTTP 401/403 hoặc
trả dữ liệu token không hợp lệ, client xóa token và phát sự kiện `auth:expired`.
Lỗi mạng, timeout/abort hoặc lỗi server khi refresh được trả về cho caller nhưng
giữ nguyên cặp token để không đăng xuất người dùng vì sự cố tạm thời.
`ConversationStoreProvider` gọi `logout` hiện có để xóa hội thoại và trạng thái
request, sau đó chuyển về `/login`. Kết quả refresh đang chờ không được khôi phục
token nếu phiên đã bị đăng xuất hoặc thay đổi.

---

## Quy ước

- Không hardcode logic endpoint trong component nếu có thể gom vào `lib/api`.
- Utility phải thuần, dễ test.
- Nếu backend schema đổi, cập nhật cả `src/types/`.
