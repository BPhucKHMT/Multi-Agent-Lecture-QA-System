# Backend — FastAPI API Service

`backend/` là backend web/API của hệ thống PUQ Q&A. Module này chịu trách nhiệm xác thực người dùng, quản lý session/chat history, stream câu trả lời AI về frontend và tích hợp Redis semantic cache.

---

## Vai trò trong hệ thống

```txt
Frontend React
  ↓ HTTP/SSE
backend/app/main.py
  ↓
API v1 endpoints
  ↓
services: auth, chat, videos, summary
  ↓
PostgreSQL + Redis + src RAG engine
```

Backend không chứa toàn bộ logic RAG. Nó gọi AI engine trong `src/`, đặc biệt là `src.rag_core.lang_graph_rag.workflow`.

---

## Cấu trúc thư mục

```txt
backend/
├── app/
│   ├── main.py              # FastAPI entry point + lifespan startup
│   ├── api/v1/endpoints/    # REST/SSE endpoints: auth, chat, videos
│   ├── core/                # Config, security, cache
│   ├── db/                  # SQLAlchemy session + Redis clients
│   ├── models/              # SQLAlchemy models: User, ChatHistory...
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic cho auth/chat/video/summary
│   └── deps.py              # FastAPI dependencies
├── alembic/                 # DB migrations
├── alembic.ini
└── requirements.txt
```

---

## Chạy backend

Từ root project:

```powershell
pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Health check:

```txt
http://localhost:8000/health
```

OpenAPI docs:

```txt
http://localhost:8000/docs
```

---

## Dịch vụ phụ thuộc

### PostgreSQL

Dùng để lưu:

- user account;
- password hash;
- refresh/session token nếu có;
- chat sessions;
- `ChatHistory` gồm cả question và response.

Biến môi trường:

```env
DATABASE_URL=postgresql+psycopg2://...
```

### Redis Stack

Dùng cho:

- JWT blacklist/rate-limit helpers hiện có;
- Redis semantic cache cho chat response;
- RediSearch vector index.

Local dev:

```powershell
docker run --name puq-redis-stack -p 6379:6379 -p 8001:8001 -v redis_stack_data:/data redis/redis-stack:latest
```

Biến môi trường:

```env
REDIS_URL=redis://localhost:6379/0
SEMANTIC_CACHE_ENABLED=True
```

---

## Chat streaming flow

```txt
POST /api/v1/chat/stream
  ↓
get_current_user + DB session + Redis binary client
  ↓
generate_chat_stream()
  ↓
Load history từ DB
  ↓
Lưu user message vào DB
  ↓
SemanticCache.get(user_message)
  ├─ Hit: stream cached text + lưu assistant vào DB
  └─ Miss: gọi LangGraph workflow từ src/rag_core
          ↓
      Stream status/token/context về frontend
          ↓
      Lưu assistant response vào DB
          ↓
      SemanticCache.set() nếu response cacheable
```

---

## API chính

| Endpoint | Mục đích |
|---|---|
| `POST /api/v1/auth/register` | Tạo tài khoản |
| `POST /api/v1/auth/login` | Đăng nhập, nhận token |
| `POST /api/v1/auth/refresh` | Làm mới access token |
| `POST /api/v1/chat/stream` | SSE stream chat AI |
| `GET /api/v1/chat/history` | Lấy lịch sử chat |
| `GET /api/v1/chat/sessions` | Lấy danh sách session |
| `GET /api/v1/videos` | Lấy danh sách video |

Tên path chính xác phụ thuộc router trong `app/api/v1/router.py`.

---

## Startup behavior

Trong `app/main.py`, lifespan startup sẽ:

1. tạo bảng DB trong dev bằng `Base.metadata.create_all()`;
2. prewarm RAG resources ở background;
3. prewarm Redis semantic cache từ N cặp Q/A gần nhất trong DB.

Nếu Redis hoặc prewarm lỗi, backend chỉ log warning/error và vẫn tiếp tục chạy.

---

## Quy ước khi sửa backend

- Comments/docstrings viết bằng tiếng Việt.
- Import dùng absolute path.
- Không để Redis cache thay PostgreSQL history.
- Với chat flow, luôn lưu user message trước cache lookup.
- Redis vector cache phải dùng client `decode_responses=False`.
