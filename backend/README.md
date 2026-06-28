# backend — FastAPI Service

`backend/` là FastAPI service chính của PUQ Q&A: auth, chat streaming, video management, PostgreSQL persistence, Redis semantic cache. Service này gọi vào `src/rag_core` để tạo câu trả lời AI.

---

## Cấu trúc thư mục chi tiết

```txt
backend/
├── requirements.txt          # Backend dependencies
├── alembic.ini               # Alembic DB migration config
├── alembic/
│   ├── README
│   ├── env.py                # Alembic environment
│   ├── script.py.mako        # Migration template
│   └── versions/
│       └── 82e56a755f71_initial_migration.py  # Initial DB migration
├── docs/
│   ├── backend.md
│   └── backend_research.md
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI entry point + lifespan startup
│   ├── deps.py               # FastAPI dependencies
│   ├── api/
│   │   ├── __init__.py
│   │   ├── README.md
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py     # API v1 router
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── auth.py   # Auth endpoints (register, login, refresh)
│   │           ├── chat.py   # Chat streaming endpoint
│   │           ├── schemas.py # Pydantic schemas
│   │           └── videos.py # Video listing endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── README.md
│   │   ├── config.py         # App configuration (Pydantic Settings)
│   │   ├── security.py       # JWT + password hashing
│   │   └── cache/
│   │       ├── __init__.py
│   │       ├── README.md
│   │       ├── prewarm.py    # Cache prewarming on startup
│   │       └── semantic.py   # Semantic cache logic (Redis)
│   ├── db/
│   │   ├── __init__.py
│   │   ├── README.md
│   │   ├── session.py        # SQLAlchemy async DB session
│   │   └── redis.py          # Redis client
│   ├── models/
│   │   ├── __init__.py
│   │   ├── README.md
│   │   └── user.py           # SQLAlchemy User model
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── README.md
│   │   └── chat.py           # Chat Pydantic schemas
│   └── services/
│       ├── __init__.py
│       ├── README.md
│       ├── auth.py           # Auth business logic
│       ├── chat.py           # Chat service (calls src.rag_core)
│       ├── summary.py        # Summary service
│       └── videos.py         # Video business logic
└── README.md
```

---

## Dependencies chính

- FastAPI 0.115.0 + uvicorn
- SQLAlchemy 2.0 + asyncpg + Alembic (PostgreSQL)
- redis 5.1.1
- python-jose + passlib (JWT + bcrypt)
- pydantic 2.9.2 + pydantic-settings
- httpx (internal HTTP calls)

---

## API endpoints

| Endpoint | Mô tả |
|---|---|
| `POST /api/v1/auth/register` | Đăng ký user mới |
| `POST /api/v1/auth/login` | Đăng nhập, nhận access + refresh token |
| `POST /api/v1/auth/refresh` | Làm mới access token |
| `POST /api/v1/auth/logout` | Đăng xuất |
| `POST /api/v1/chat/stream` | Stream chat SSE (status, token, context, metadata) |
| `GET /api/v1/videos` | Danh sách video bài giảng |

---

## Chat streaming contract

Backend gửi SSE events về frontend:

```json
{"type":"status","status":"Đang truy hồi tri thức..."}
{"type":"token","content":"Nội dung trả lời..."}
{"type":"context","docs":[...]}
{"type":"metadata","conversation_id":"...","response":{...}}
{"type":"error","content":"..."}
{"type":"[DONE]"}
```

---

## Chạy backend

```powershell
# Cài dependencies
pip install -r backend/requirements.txt

# Chạy dev server
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Database

- PostgreSQL là **source of truth** cho user, session và chat history.
- Alembic quản lý migrations trong `backend/alembic/`.
- Redis chỉ là cache; mất Redis thì rebuild từ DB bằng prewarm.

---

## Quy ước khi sửa backend

- Endpoint mới thêm vào `app/api/v1/endpoints/` và register trong `router.py`.
- Service logic để trong `app/services/`, không nhét trực tiếp vào endpoint.
- Pydantic schemas để trong `app/schemas/`.
- Khi sửa chat stream, kiểm tra đủ event types: `status`, `token`, `context`, `metadata`, `error`, `[DONE]`.
