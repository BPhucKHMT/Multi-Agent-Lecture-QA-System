# services — Backend Business Logic

`backend/app/services/` chứa logic nghiệp vụ phía backend. Endpoint FastAPI gọi vào service để xử lý request, còn service có thể gọi DB, Redis hoặc AI engine trong `src/`.

---

## Cấu trúc

```txt
services/
├── auth.py     # Register/login/password hashing/token flow
├── chat.py     # Streaming chat, DB history, Redis cache, LangGraph call
├── videos.py   # Video metadata/index service
└── summary.py  # Summary Hub service
```

---

## Chat service

`chat.py` là file quan trọng nhất trong service layer.

Flow chính:

```txt
Load history từ PostgreSQL
  ↓
Lưu user message
  ↓
Check Redis semantic cache
  ├─ Hit: stream cached response + lưu assistant
  └─ Miss: gọi LangGraph workflow
          ↓
      Stream tokens/context/status
          ↓
      Lưu assistant response
          ↓
      Ghi Redis nếu cacheable
```

---

## Nguyên tắc

- Endpoint không nên chứa business logic phức tạp.
- Service được phép biết DB model và integration details.
- Với chat, không bỏ bước lưu DB kể cả khi cache hit.
- Exception trong stream cần trả event `error` và `[DONE]` để frontend không treo.
