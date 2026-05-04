# api — FastAPI Routers

`backend/app/api/` chứa tầng HTTP routing của backend. Các endpoint ở đây chỉ nên nhận request, gọi service tương ứng và trả response/stream về client.

---

## Cấu trúc

```txt
api/
└── v1/
    ├── router.py          # Gắn các endpoint group vào API v1
    └── endpoints/
        ├── auth.py        # Register/login/refresh/logout
        ├── chat.py        # SSE chat stream/history/sessions
        ├── videos.py      # Video list/metadata
        └── schemas.py     # Request/response schema cục bộ cho endpoint
```

---

## Nguyên tắc

- Endpoint mỏng, business logic để trong `backend/app/services/`.
- Auth dependency dùng `get_current_user` từ `deps.py`.
- DB session lấy qua `get_db`.
- Redis semantic cache trong chat endpoint dùng `get_redis_binary`.

---

## Chat endpoint

`POST /api/v1/chat/stream` trả Server-Sent Events:

```txt
status -> token -> context -> metadata -> [DONE]
```

Frontend phải xử lý event stream thay vì chờ JSON response một lần.
