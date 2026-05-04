# core — Backend Core Utilities

`backend/app/core/` chứa cấu hình và tiện ích nền tảng dùng chung trong backend.

---

## Cấu trúc

```txt
core/
├── config.py       # Settings đọc từ .env
├── security.py     # Password hashing/JWT helpers
└── cache/          # Redis semantic cache
```

---

## Config

`config.py` đọc `.env` và tạo singleton `settings`.

Nhóm config chính:

- app metadata;
- database URL;
- Redis semantic cache;
- OpenAI model/API key;
- JWT;
- CORS.

---

## Security

`security.py` xử lý các phần liên quan auth như:

- hash/verify password;
- tạo/verify JWT;
- token expiration.

---

## Cache

Xem chi tiết tại [cache/README.md](cache/README.md).
