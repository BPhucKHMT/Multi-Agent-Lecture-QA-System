# Hướng dẫn chạy/deploy PUQ Q&A (cập nhật theo cấu trúc src/)

## 1) Kiến trúc runtime hiện tại

- **Backend**: `server.py` (FastAPI bootstrap, mount `src.api.router`)
- **Frontend**: `app.py` (Streamlit UI)
- **RAG core**: `src/rag_core/*`
- **Ingestion pipeline**: `src/ingestion/data_loader/pipeline.py` (giữ bridge `python -m data_loader.pipeline`)

> Lưu ý: backend hiện lưu hội thoại **in-memory** trong `src/api/services/chat_service.py`.

## 2) Yêu cầu hệ thống

- Python 3.12+
- pip
- (Tùy chọn) Docker + Docker Compose
- API keys hợp lệ trong `.env`

## 3) Cấu hình môi trường

Tạo `.env` từ `.env.example` và điền các biến cần thiết:

```bash
googleAPIKey=...
myAPIKey=...
GEMINI_API_KEY=...
YOUTUBE_API_KEY=...
```

## 4) Chạy local (development)

### Backend

```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
streamlit run app.py
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:8501`

## 5) Chạy bằng Docker Compose

```bash
docker-compose up --build
```

Compose hiện chạy chung FastAPI + Streamlit trong service `app`.

## 6) Verify nhanh sau deploy

### Root endpoint

```bash
curl http://localhost:8000/
```

Kỳ vọng:

```json
{"message":"PUQ Q&A Backend API","status":"running"}
```

### Chat endpoint contract

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"conversation_id\":\"demo\",\"messages\":[],\"user_message\":\"Xin chào\"}"
```

Kỳ vọng response có các trường ngoài: `conversation_id`, `response`, `updated_at`.

## 7) Chạy ingestion pipeline

Giữ tương thích lệnh cũ:

```bash
python -m data_loader.pipeline
```

Hoặc gọi trực tiếp module mới:

```bash
python -m src.ingestion.data_loader.pipeline
```

## 8) Ghi chú hardening production

- Không để `allow_origins=["*"]`; cần whitelist domain frontend thật.
- Chạy backend bằng process manager (systemd/supervisor/container restart policy).
- Theo dõi logs backend và timeout upstream cho request `/chat`.
