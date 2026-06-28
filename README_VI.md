# RAG QABot — Multi-Agent Lecture QA System

PUQ Q&A là hệ thống hỏi đáp bài giảng cho sinh viên UIT, kết hợp **Retrieval-Augmented Generation (RAG)**, **LangGraph Multi-Agent Supervisor**, FastAPI backend, React frontend, PostgreSQL và Redis semantic cache.

Mục tiêu: người dùng có thể hỏi về nội dung bài giảng/video, nhận câu trả lời tiếng Việt có citation, hoặc chuyển sang các tác vụ chuyên biệt như giải toán, hỗ trợ code và tạo quiz.

## Demo Preview

| Chat Interface | Multi-Agent Workflow |
|---|---|
| ![Demo giao diện chat](public/Demo1.png) | ![Demo workflow agent](public/Demo2.png) |

![Demo tổng quan hệ thống](public/Demo3.png)
![Demo mở rộng hệ thống](public/Demo4.png)

---

## Chạy nhanh bằng Docker

Docker Compose hiện chạy theo **profiles** để tách container rõ ràng:

```txt
frontend -> React/Vite dev server, http://localhost:5173
api-cpu -> FastAPI/RAG CPU, http://localhost:8000
api-gpu -> FastAPI/RAG GPU local, http://localhost:8000
redis-stack -> Redis Stack + RedisInsight, http://localhost:8001
pipeline-cpu -> Data pipeline CPU, chạy khi cần ingest dữ liệu
pipeline-gpu -> Data pipeline GPU, chạy khi cần ingest dữ liệu bằng GPU
```

> Frontend và backend là **2 container riêng**, nhưng được quản lý chung trong `docker-compose.yaml`.

### 1. Chuẩn bị `.env`

```powershell
Copy-Item .env.example .env
```

Sau đó điền các biến cần thiết như `myAPIKey`, `DATABASE_URL`, `JWT_SECRET`, `REDIS_URL`.

### 2. Chạy local CPU: frontend + backend + Redis

```powershell
docker compose --profile cpu --profile frontend --profile redis up --build
```

Truy cập:

```txt
Frontend: http://localhost:5173
Backend API: http://localhost:8000
RedisInsight: http://localhost:8001
```

### 3. Chạy local GPU: backend GPU + Redis

Dùng khi máy local có NVIDIA GPU, Docker Desktop đã bật GPU support/NVIDIA Container Toolkit.

```powershell
docker compose --profile gpu --profile redis up --build
```

Lệnh trên chạy **2 service**: `api-gpu` + `redis-stack`.

Nếu muốn chạy cùng lúc **3 service** (frontend + backend GPU + Redis):

```powershell
docker compose --profile gpu --profile redis --profile frontend up --build
```

Image GPU đã test build local:

```txt
rag-qabot:gpu = 12.5GB
```

### 4. Chạy data pipeline bằng Docker

CPU pipeline:

```powershell
docker compose --profile pipeline run --rm pipeline-cpu
```

GPU pipeline:

```powershell
docker compose --profile pipeline-gpu run --rm pipeline-gpu
```

Pipeline image chứa OCR/Whisper/video dependencies nặng, được tách riêng khỏi image deploy API.

### 5. Build image riêng nếu cần đo size

CPU runtime:

```powershell
docker build --target prod-cpu -t rag-qabot:cpu-runtime .
docker images rag-qabot:cpu-runtime
```

GPU runtime/dev:

```powershell
docker build --target dev-gpu -t rag-qabot:gpu .
docker images rag-qabot:gpu
```

Size đã đo gần nhất:

```txt
rag-qabot:cpu-runtime = 3.97GB
rag-qabot:gpu = 12.5GB
```

---

## Chạy Local (Không dùng Docker)

Nếu bạn muốn chạy hệ thống trực tiếp trên máy host không qua Docker:

### Yêu cầu hệ thống

1. **Python 3.12+**
2. **Node.js** (v18 trở lên) & **npm**
3. **PostgreSQL** (chạy local hoặc trên cloud)
4. **Redis** (chạy local, yêu cầu cho tính năng semantic cache)

### Bước 1: Cài đặt Python Dependencies

Khởi tạo và kích hoạt môi trường ảo (virtual environment), sau đó cài đặt các gói cần thiết:

```powershell
# Tạo môi trường ảo
python -m venv venv

# Kích hoạt môi trường ảo
# Trên Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Trên Linux/macOS:
source venv/bin/activate

# Cài đặt thư viện
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

### Bước 2: Cấu hình biến môi trường

Tạo file `.env` từ file mẫu:

```powershell
cp .env.example .env
```

Mở file `.env` và cập nhật các thông số cần thiết:
- `DATABASE_URL`: Connection string đến PostgreSQL database của bạn (ví dụ: `postgresql://postgres:password@localhost:5432/rag_qabot`)
- `myAPIKey`: OpenAI API key của bạn
- `REDIS_URL`: URL kết nối tới Redis của bạn (ví dụ: `redis://localhost:6379/0`)

### Bước 3: Chạy Database Migration

Áp dụng database schema vào PostgreSQL của bạn bằng Alembic:

```powershell
cd backend
alembic upgrade head
cd ..
```

### Bước 4: Khởi chạy các dịch vụ

1. **Khởi động Redis**:
   Đảm bảo Redis server đang chạy (mặc định tại cổng `6379`).
2. **Chạy API Backend**:
   ```powershell
   python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
3. **Chạy Frontend**:
   Mở một terminal mới:
   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

Bây giờ bạn có thể truy cập giao diện ứng dụng tại: `http://localhost:5173`.

---

## Tài khoản demo

```txt
Email: nguyenlam.baophuc@gmail.com
Password: 123456789
```

---

## Tính năng chính

- **Chat RAG tiếng Việt**: hỏi đáp từ transcript bài giảng.
- **Citation video**: trả link/timestamp nguồn khi có context phù hợp.
- **Multi-Agent Supervisor**: tự route sang tutor, coding, math, quiz hoặc direct.
- **Math Agent**: dùng SymPy để tính toán rồi trình bày lại bằng LaTeX.
- **Coding Agent**: sinh, chạy và tự sửa code trong sandbox khi phù hợp.
- **Quiz Agent**: tạo câu hỏi trắc nghiệm từ nội dung học.
- **Summary Hub**: xem danh sách video và tóm tắt nội dung.
- **Auth + History**: đăng nhập, lưu session và lịch sử chat trong PostgreSQL.
- **Redis semantic cache**: cache exact/semantic response để giảm latency và token.

---

## Kiến trúc tổng quan

```mermaid
flowchart TD
User[Browser] --> FE[React + Vite Frontend]
FE --> API[FastAPI Backend]
API --> Auth[Auth + PostgreSQL]
API --> Chat[Chat Service]
Chat --> Redis[Redis Stack Semantic Cache]
Chat --> Graph[LangGraph Supervisor]
Graph --> Tutor[Tutor RAG Agent]
Graph --> Code[Coding Agent]
Graph --> Math[Math Agent]
Graph --> Quiz[Quiz Agent]
Graph --> Direct[Direct Agent]
Tutor --> Retrieval[Hybrid Search + Reranker]
Retrieval --> Chroma[ChromaDB]
Retrieval --> Artifacts[artifacts/data, videos, chunks]
Graph --> LLM[OpenAI Chat Model]
```

---

## Cấu trúc thư mục chi tiết

```txt
final_project/
├── backend/            # FastAPI service: auth, chat, DB, Redis cache
│   ├── app/
│   │   ├── api/        # REST endpoints (auth, chat, videos)
│   │   │   └── v1/
│   │   │       ├── router.py       # API v1 router
│   │   │       └── endpoints/      # auth, chat, videos, schemas
│   │   ├── core/       # Config, security, Redis semantic cache
│   │   │   └── cache/   # prewarm, semantic cache logic
│   │   ├── db/         # PostgreSQL session, Redis client
│   │   ├── models/     # SQLAlchemy User model
│   │   ├── schemas/    # Pydantic schemas
│   │   └── services/   # Business logic (auth, chat, summary, videos)
│   ├── alembic/        # DB migrations (Alembic)
│   ├── docs/           # Backend-specific docs
│   └── requirements.txt
├── frontend/           # React + Vite UI
│   ├── src/
│   │   ├── app/        # App shell, routing, providers
│   │   │   └── layouts/
│   │   │       └── MainLayout.tsx
│   │   ├── components/ # Chat, sidebar, shared UI
│   │   │   ├── chat/   # ChatInput, MessageList, CitationList, MarkdownRenderer
│   │   │   ├── shared/ # Icons
│   │   │   └── sidebar/ # ConversationSidebar
│   │   ├── lib/        # API clients, utilities
│   │   │   ├── api/    # client, chat (SSE), videos
│   │   │   └── utils/  # citation, timestamp formatting
│   │   ├── pages/      # Gateway, Login, Register, Workspace
│   │   ├── store/      # Zustand state management
│   │   ├── styles/     # Global CSS/Tailwind
│   │   └── types/      # TypeScript types (api, app, rag)
│   ├── ui2figma/       # Tool xuất UI sang Figma (separate module)
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── src/                # AI/RAG engine
│   ├── rag_core/       # LangGraph supervisor + 5 agents + tools
│   │   ├── lang_graph_rag.py   # Graph chính + supervisor + routing
│   │   ├── state.py            # State schema
│   │   ├── resource_manager.py # Prewarm resources
│   │   ├── router_patterns.py  # Deterministic steering
│   │   ├── offline_rag.py      # Legacy RAG flow
│   │   ├── agents/
│   │   │   ├── tutor.py        # RAG agent + citation
│   │   │   ├── coding.py       # Lập trình + sandbox
│   │   │   ├── coding_retrieval.py  # Retrieval helper cho coding
│   │   │   ├── math.py         # SymPy + LaTeX
│   │   │   ├── quiz.py         # Tạo câu hỏi trắc nghiệm
│   │   │   └── direct.py       # Chào hỏi, tổng quát
│   │   └── tools/
│   │       └── sandbox.py      # Sandbox chạy code an toàn
│   ├── retrieval/      # Hybrid search, BM25, reranker, chunkers
│   │   ├── hybrid_search.py    # Vector + BM25 fusion
│   │   ├── keyword_search.py   # BM25 đơn lẻ
│   │   ├── reranking.py        # CrossEncoder reranker
│   │   └── text_splitters/     # Chunking strategies
│   ├── storage/        # ChromaDB vectorstore
│   ├── generation/     # LLM factory (ChatOpenAI)
│   ├── data_pipeline/  # Crawl/load/preprocess/chunk lecture data
│   │   ├── combine_content.py
│   │   └── data_loader/
│   │       ├── coordinator.py      # Pipeline coordinator
│   │       ├── file_loader.py      # File loading
│   │       ├── keyframe_extractor.py
│   │       ├── llm_utils.py
│   │       ├── ocr_processor.py    # OCR (EasyOCR)
│   │       ├── pipeline.py         # Main pipeline entry
│   │       ├── pipeline_state.py
│   │       ├── preprocess.py
│   │       ├── scene_detector.py   # TransNetV2
│   │       ├── video_downloader.py
│   │       ├── youtube_fetchers.py # YouTube transcript
│   │       └── artifacts/data_extraction/SceneJSON/
│   ├── shared/         # Shared config, logging
│   └── notebook_baseline/ # Research notebooks + images
├── experiments/        # Benchmark & evaluation
│   ├── configs/        # YAML configs
│   │   ├── embedding/  # ~30+ configs (recursive, timestamp, parent_child)
│   │   └── index/      # Config build ChromaDB index
│   ├── docs/
│   │   ├── data/groundtruth.md  # Hướng dẫn tạo GT dataset
│   │   └── evaluation/          # Báo cáo benchmark
│   │       ├── end_to_end_retrieval.md  # 22-config (MAIN)
│   │       ├── embedding.md             # 7 embedding models
│   │       ├── reranker.md              # 6 reranker models
│   │       └── qa_metrics.md            # BERTScore + RAGAS
│   ├── indexes/        # ChromaDB indexes đã build
│   ├── runs/           # Benchmark outputs
│   │   ├── e2e_reranked/
│   │   ├── e2e_retrieval/
│   │   ├── embedding/
│   │   ├── finetune/embedding/, finetune/reranker/
│   │   ├── hybrid/
│   │   ├── qa_metrics/ # JSONL predictions + report
│   │   └── reranker/
│   ├── scripts/        # ~25 CLI scripts
│   │   ├── benchmark_*.py       # Runners
│   │   ├── build_index.py       # Build ChromaDB
│   │   ├── finetune_*.py        # Fine-tune
│   │   ├── generate_*.py        # Chunk/query generation
│   │   └── ...
│   ├── src/            # Core library
│   │   ├── benchmark/  # Runners
│   │   ├── evaluation/ # Metrics
│   │   ├── indexing/   # Index builders
│   │   ├── qrels/      # Qrels processing
│   │   └── reranker/   # Reranker eval
│   ├── tests/          # 17 unit tests
│   └── scratch/        # Throwaway experiments
├── artifacts/          # Runtime data
│   ├── data/           # Transcript/raw/processed
│   ├── chunks/         # Cached chunks
│   ├── database_semantic/ # ChromaDB persistent store
│   └── videos/         # Metadata + thumbnails
├── docs/               # Design docs, upgrade plans
├── tests/              # Project-level smoke tests
├── requirements.txt    # Core AI/RAG dependencies
├── backend/requirements.txt  # Backend-only
├── config.yaml         # Playlist/source config
└── .env.example        # Mẫu biến môi trường
```

---

## Các README theo khu vực

- [backend/README.md](backend/README.md): FastAPI, PostgreSQL, Redis, auth, chat API.
- [src/README.md](src/README.md): AI engine, LangGraph agents, retrieval và pipeline.
- [frontend/README.md](frontend/README.md): React UI, cấu trúc component, scripts.
- [src/rag_core/README.md](src/rag_core/README.md): Supervisor và agent workflow.
- [src/retrieval/README.md](src/retrieval/README.md): Hybrid search, BM25, reranking.
- [src/data_pipeline/README.md](src/data_pipeline/README.md): Crawl/xử lý dữ liệu bài giảng.
- [backend/app/core/cache/README.md](backend/app/core/cache/README.md): Redis semantic cache.

---

## Biến môi trường quan trọng

Copy `.env.example` thành `.env`, rồi điền các biến thực tế.

| Biến | Mục đích |
|---|---|
| `DATABASE_URL` | PostgreSQL/Supabase connection string |
| `JWT_SECRET` | Secret ký access/refresh token |
| `myAPIKey` | OpenAI API key cho LLM/embedding |
| `OPENAI_MODEL` | Model chat chính |
| `REDIS_URL` | Redis Stack URL, mặc định `redis://localhost:6379/0` |
| `SEMANTIC_CACHE_ENABLED` | Bật/tắt Redis semantic cache |
| `YOUTUBE_API_KEY` | Dùng khi crawl playlist YouTube |
| `PUQ_DATA_DIR` | Thư mục transcript/data |
| `PUQ_VECTOR_DB_DIR` | Thư mục ChromaDB |
| `PUQ_VIDEOS_DIR` | Thư mục metadata video |

---

## Workflow request chat

```txt
User gửi câu hỏi
↓
Frontend stream request tới /api/v1/chat/stream
↓
Backend lưu user message vào PostgreSQL
↓
Redis exact/semantic cache lookup
├─ Hit: stream response cache + lưu assistant vào DB
└─ Miss: gọi LangGraph workflow
↓
Supervisor route agent
↓
Agent tạo response
↓
Lưu assistant vào DB
↓
Nếu cacheable thì ghi Redis
```

---

## Data/RAG workflow

```txt
YouTube/transcript data
↓
Data pipeline xử lý nội dung
↓
Chunking + metadata
↓
Embedding vào ChromaDB
↓
Runtime retrieval: vector + keyword
↓
Reranker chọn context tốt nhất
↓
Tutor agent sinh câu trả lời có citation
```

---

## Lệnh hữu ích

### Cài Python dependencies

```powershell
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

### Chạy backend

```powershell
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Chạy frontend

```powershell
npm --prefix frontend install
npm --prefix frontend run dev
```

### Chạy Redis local

Nếu đã cài Redis local sẵn trên máy:

```powershell
redis-server
```

Hoặc chạy bằng Docker:

```powershell
docker compose --profile redis up -d redis-stack
```

Redis endpoint local:

```txt
REDIS_URL=redis://localhost:6379/0
RedisInsight: http://localhost:8001
```

### Chạy data pipeline

```powershell
python -m src.data_pipeline.pipeline
```

### Compile nhanh Python files đã sửa

```powershell
python -m compileall backend/app src
```

---

## Lưu ý vận hành

- PostgreSQL là **source of truth** cho user, session và chat history.
- Redis chỉ là cache; mất Redis thì có thể rebuild từ DB bằng prewarm.
- `artifacts/` là runtime data lớn, thường không commit toàn bộ.
- Backend startup sẽ prewarm RAG resources và Redis cache ở background.
- Prompt/response/UI ưu tiên tiếng Việt.

---

## Benchmark & Đánh giá

Toàn bộ pipeline benchmark nằm trong `experiments/`. Xem [experiments/README.md](experiments/README.md) để biết cách setup và reproduce.

### Tóm tắt kết quả benchmark

22 configs được test qua các strategy chunking, embedding models và rerankers. Winner: **C21** — hybrid search + chunking `timestamp_150_50_raw` + embedding `bge_m3-finetuned-v3` + Jina reranker.

| Config | Chunk strategy | Embedding | Hit@5 | MRR@10 | NDCG@10 |
|---|---|---|---:|---:|---:|
| **C21** | `timestamp_150_50_raw` | `bge_m3-finetuned-v3` | **0.9467** | **0.8085** | **0.6092** |
| C02 | `recursive` | `bge_m3` | 0.8967 | 0.7471 | 0.5205 |
| C19 | `semantic` | `bge_m3-finetuned-v3` | 0.9033 | 0.7387 | 0.5355 |
| C22 | `parent_child_180s_45s` | `bge_m3-finetuned-v3` | 0.9067 | 0.6723 | 0.5494 |

### Báo cáo đánh giá chi tiết

- [End-to-end retrieval benchmark (22 configs)](experiments/docs/evaluation/end_to_end_retrieval.md) — bảng kết quả đầy đủ, phân tích winner
- [So sánh embedding models (7 models)](experiments/docs/evaluation/embedding.md) — BGE-M3 variants, multilingual-e5-large, halong_embedding
- [So sánh reranker models (6 models)](experiments/docs/evaluation/reranker.md) — Jina v2 thắng, phân tích latency
- [QA quality metrics (BERTScore + RAGAS)](experiments/docs/evaluation/qa_metrics.md) — faithfulness, context precision/recall, answer relevancy
- [**Báo cáo Ablation Study**](docs/ablation_report.md) — 4 giai đoạn bóc tách: embedding → reranker → chunking (E2E) → chất lượng sinh. Giải thích lý do chọn C21 làm cấu hình production.


### Reproduce benchmarks

```powershell
# Build ChromaDB index
python experiments/scripts/build_index.py --config experiments/configs/index/<config>.yaml

# Chạy end-to-end retrieval benchmark
python experiments/scripts/benchmark_end_to_end_retrieval.py

# Chạy embedding benchmark
python experiments/scripts/benchmark_embeddings.py --config experiments/configs/embedding/<config>.yaml

# Chạy reranker benchmark
python experiments/scripts/benchmark_rerankers.py

# Chạy QA quality benchmark (BERTScore + RAGAS)
python experiments/scripts/benchmark_qa_metrics.py
```

Output lưu trong `experiments/runs/`.

---

## Tài liệu nâng cấp liên quan

- [Redis plan](docs/upgrade_system/redis.md)
- [Redis architecture](docs/upgrade_system/redis_architecture.md)
- [Deployment notes](DEPLOYMENT.md)
- [Agent rules](AGENTS.md)
- [Fine-tuned Embedding Model Card](models/bge-m3-finetuned/MODEL_CARD.md) — chi tiết huấn luyện, bộ dữ liệu, hyperparameters, kết quả đánh giá cho `bge-m3-finetuned-v3`
