# db — Database & Redis Clients

`backend/app/db/` chứa các helper kết nối dữ liệu cho backend.

---

## Cấu trúc

```txt
db/
├── session.py  # SQLAlchemy engine, SessionLocal, get_db dependency
└── redis.py    # Redis singleton clients + helper blacklist/rate-limit
```

---

## PostgreSQL

`session.py` tạo SQLAlchemy engine từ:

```env
DATABASE_URL=...
```

FastAPI endpoint lấy session qua dependency:

```python
db: Session = Depends(get_db)
```

---

## Redis

`redis.py` có 2 client singleton:

| Helper | decode | Dùng cho |
|---|---:|---|
| `get_redis()` | `decode_responses=True` | auth/rate-limit/string values |
| `get_redis_binary()` | `decode_responses=False` | semantic cache vector binary |

Semantic cache không dùng client text vì embedding được lưu dạng bytes.

---

## Lưu ý

- Không tạo Redis/DB connection mới ở từng function nếu có dependency/singleton sẵn.
- Đóng DB session sau request bằng `get_db` hoặc `SessionLocal` trong `finally`.
- Redis chỉ là cache, không phải source of truth cho chat history.
