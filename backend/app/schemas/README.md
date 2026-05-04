# schemas — Pydantic Contracts

`backend/app/schemas/` chứa Pydantic schemas dùng để validate request/response ở backend.

---

## Vai trò

Schemas giúp tách biệt:

```txt
HTTP request/response contract
khỏi
SQLAlchemy database models
```

Điều này tránh expose field nhạy cảm từ DB ra frontend.

---

## Khi nào thêm schema?

- Thêm endpoint mới.
- Response cần shape rõ ràng cho frontend.
- Request body cần validation.
- Muốn tránh trả trực tiếp ORM model.

---

## Nguyên tắc

- Không đưa password hash hoặc secret vào response schema.
- Field đặt tên rõ nghĩa, tương thích frontend types.
- Nếu schema thay đổi, kiểm tra `frontend/src/types/` và API client.
