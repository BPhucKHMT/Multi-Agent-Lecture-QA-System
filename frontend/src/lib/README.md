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

---

## Quy ước

- Không hardcode logic endpoint trong component nếu có thể gom vào `lib/api`.
- Utility phải thuần, dễ test.
- Nếu backend schema đổi, cập nhật cả `src/types/`.
