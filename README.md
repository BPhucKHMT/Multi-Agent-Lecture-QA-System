# RAG QABot — Multi-Agent Lecture QA System

[Tiếng Việt](README_VI.md)

PUQ Q&A is a lecture question-answering system for UIT students. It combines **Retrieval-Augmented Generation (RAG)**, a **LangGraph Multi-Agent Supervisor**, a FastAPI backend, a React frontend, PostgreSQL, and Redis semantic caching.

The goal is to let users ask questions about lecture/video content, receive Vietnamese answers with citations, or switch to specialized tasks such as math solving, coding support, and quiz generation.

## Demo Preview

| Chat Interface | Multi-Agent Workflow |
|---|---|
| ![Chat interface demo](public/Demo1.png) | ![Agent workflow demo](public/Demo2.png) |

![System overview demo](public/Demo3.png)
![System extension demo](public/Demo4.png)

---

## Quick Start with Docker

Docker Compose uses **profiles** to separate services clearly:

```txt
frontend -> React/Vite dev server, http://localhost:5173
api-cpu -> FastAPI/RAG CPU, http://localhost:8000
api-gpu -> FastAPI/RAG local GPU, http://localhost:8000
redis-stack -> Redis Stack + RedisInsight, http://localhost:8001
pipeline-cpu -> CPU data pipeline, used when ingesting data
pipeline-gpu -> GPU data pipeline, used when ingesting data with GPU support
```

> Frontend and backend run as **two separate containers**, managed together by `docker-compose.yaml`.

### 1. Prepare `.env`

```powershell
Copy-Item .env.example .env
```

Then fill in `myAPIKey`, `DATABASE_URL`, `JWT_SECRET`, and `REDIS_URL`. For
monitoring, also set a strong `GRAFANA_ADMIN_PASSWORD` in `.env`. It is not
needed when using `-NoMonitoring`. The password stays local (`.env` is ignored
by Git). On Windows, install native `windows_exporter` on port 9182 and set
`PUQ_PROMETHEUS_CONFIG=prometheus-windows.yml` to collect host CPU/RAM
metrics (GPU only if the exporter/driver exposes them); otherwise Prometheus
only scrapes the API. Langfuse traces remain
hosted in Langfuse Cloud and require their own keys.

### 2. Run the local CPU stack

From PowerShell, one entry point selects CPU + frontend + Redis + monitoring:

```powershell
.\dev.ps1 up                 # start; use -Build after changing image/dependencies
.\dev.ps1 restart            # restart API after Python code changes
.\dev.ps1 status             # running services
.\dev.ps1 logs api-cpu       # follow API logs; omit name for all services
.\dev.ps1 down               # stop all project services; keep data volumes
```

Grafana: http://127.0.0.1:3001 (credentials from `.env`) ·
Prometheus: http://127.0.0.1:9091 · RedisInsight: http://127.0.0.1:8001.

To run only the app without Grafana or a Grafana password, run
`.\dev.ps1 down` when changing modes, then add `-NoMonitoring` to `up`,
`status` and `logs` (for example `.\dev.ps1 up -NoMonitoring`).

To use external Redis, set a container-reachable
`REDIS_URL`, stop any previously started stack, then run
`.\dev.ps1 up -ExternalRedis`. This starts API, frontend, Prometheus and
Grafana without starting local Redis; add `-NoMonitoring` to omit monitoring.
The external Redis must be ready before sending chat requests.

On Linux, use Compose directly: set `PUQ_PROMETHEUS_CONFIG=prometheus-linux.yml`
in `.env`, then run
`docker compose -f docker-compose.yaml -f docker-compose.observability.yaml --profile cpu --profile frontend --profile monitoring --profile linux-monitoring up -d`.
For NVIDIA host metrics, use `prometheus-linux-gpu.yml` and add
`--profile nvidia-monitoring`. For an app-only run (no Grafana password),
use `docker compose --profile cpu --profile frontend up -d`.

Open:

```txt
Frontend: http://localhost:5173
Backend API: http://localhost:8000
RedisInsight: http://localhost:8001
```

### 3. Run the local GPU stack

Requires NVIDIA GPU and a working Docker GPU runtime. Stop the CPU stack
before switching (`.\dev.ps1 down`); both APIs use port 8000.

```powershell
.\dev.ps1 up -Gpu                 # GPU + frontend + Redis + monitoring
.\dev.ps1 up -Gpu -NoFrontend     # GPU + Redis + monitoring, no frontend
```

Add `-NoMonitoring` to either command if you do not need Prometheus/Grafana.

Locally tested GPU image size:

```txt
rag-qabot:gpu = 12.5GB
```

### 4. Run the data pipeline with Docker

CPU pipeline:

```powershell
docker compose --profile pipeline run --rm pipeline-cpu
```

GPU pipeline:

```powershell
docker compose --profile pipeline-gpu run --rm pipeline-gpu
```

The pipeline image contains heavy OCR/Whisper/video dependencies and is separated from the API deployment image.

### 5. Build standalone images for size checks

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

Latest measured sizes:

```txt
rag-qabot:cpu-runtime = 3.97GB
rag-qabot:gpu = 12.5GB
```

---

## Run Locally (Without Docker)

If you prefer to run the system directly on your host machine without Docker:

### Prerequisites

1. **Python 3.12+**
2. **Node.js** (v18 or higher) & **npm**
3. **PostgreSQL** (running locally or in the cloud)
4. **Redis** (running locally, required for auth revocation and semantic cache)

### Step 1: Install Python Dependencies

Create and activate a virtual environment, then install the required libraries:

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

### Step 2: Configure Environment Variables

Create your `.env` file from the template:

```powershell
cp .env.example .env
```

Open `.env` and fill in the necessary values:
- `DATABASE_URL`: Your PostgreSQL connection string (e.g. `postgresql://postgres:password@localhost:5432/rag_qabot`)
- `myAPIKey`: Your OpenAI API key
- `REDIS_URL`: Your Redis connection URL (e.g. `redis://localhost:6379/0`)

### Step 3: Run Database Migrations

Apply the database schema to your PostgreSQL instance using Alembic:

```powershell
cd backend
alembic upgrade head
cd ..
```

### Step 4: Run the Services

1. **Start Redis**:
   Make sure your Redis server is running (typically on `localhost:6379`).
2. **Run Backend API**:
   ```powershell
   python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
3. **Run Frontend**:
   In a separate terminal:
   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

Open your browser at `http://localhost:5173`.

---

## Demo account

Create a test account at `/register`. Never commit credentials to this repository.

---

## Key Features

- **Vietnamese RAG chat**: answer questions from lecture transcripts.
- **Video citations**: return source links/timestamps when relevant context is found.
- **Multi-Agent Supervisor**: routes requests to tutor, coding, math, quiz, or direct agents.
- **Math Agent**: uses SymPy for calculation and explains results with LaTeX.
- **Coding Agent**: generates, executes, and self-corrects code in a sandbox when appropriate.
- **Quiz Agent**: generates multiple-choice questions from learning content.
- **Summary Hub**: browse videos and lecture summaries.
- **Auth + History**: login, sessions, and chat history stored in PostgreSQL.
- **Redis semantic cache**: exact/semantic response caching to reduce latency and token usage.

---

## Architecture Overview

![Architecture Overview](public/architecture.png)

---

## Main Directory Structure

```txt
final_project/
├── backend/            # Modular FastAPI app: auth, chat, DB, Redis cache
│   ├── app/
│   │   ├── api/        # REST endpoints (auth, chat, videos)
│   │   ├── core/       # Config, security, Redis semantic cache
│   │   ├── db/         # PostgreSQL session, Redis client
│   │   ├── models/     # SQLAlchemy User model
│   │   ├── schemas/    # Pydantic schemas
│   │   └── services/   # Business logic (auth, chat, summary, videos)
│   ├── alembic/        # DB migrations
│   └── requirements.txt
├── frontend/           # React + Vite UI
│   ├── src/
│   │   ├── app/        # App shell, routing, providers
│   │   ├── components/ # Chat, sidebar, shared UI
│   │   ├── lib/        # API clients, utilities
│   │   ├── pages/      # Gateway, Login, Workspace
│   │   ├── store/      # React Context state management
│   │   ├── styles/     # Global CSS
│   │   └── types/      # TypeScript types
│   └── ui2figma/       # Figma integration tool
├── src/                # AI/RAG engine
│   ├── rag_core/       # LangGraph supervisor + 5 agents + tools
│   ├── retrieval/      # Hybrid search, BM25, reranker, chunkers
│   ├── storage/        # ChromaDB vectorstore
│   ├── generation/     # LLM factory (ChatOpenAI)
│   ├── data_pipeline/  # Crawl/load/preprocess/chunk lecture data
│   │   └── data_loader/ # OCR, scene detection, video download
│   ├── shared/         # Shared config, logging
│   └── notebook_baseline/ # Research notebooks
├── experiments/        # Benchmark & evaluation
│   ├── configs/        # YAML configs (embedding, index)
│   ├── docs/           # Evaluation reports, ground truth guide
│   ├── scripts/        # CLI runners (benchmark, fine-tune, build)
│   ├── src/            # Core library (metrics, benchmark, indexing)
│   ├── tests/          # Unit tests
│   └── runs/           # Benchmark outputs
├── artifacts/          # Runtime data: transcripts, chunks, ChromaDB, videos
├── docs/               # Design docs, upgrade plans
├── tests/              # Project-level smoke tests
├── requirements.txt    # Core AI/RAG dependencies
├── backend/requirements.txt  # Backend-only dependencies
├── config.yaml         # Playlist/source config cho data pipeline
└── .env.example        # Environment variable template
```

---

## Area-Specific READMEs

- [backend/README.md](backend/README.md): FastAPI, PostgreSQL, Redis, auth, chat API.
- [src/README.md](src/README.md): AI engine, LangGraph agents, retrieval, and pipeline.
- [frontend/README.md](frontend/README.md): React UI, component structure, scripts.
- [src/rag_core/README.md](src/rag_core/README.md): Supervisor and agent workflow.
- [src/retrieval/README.md](src/retrieval/README.md): Hybrid search, BM25, reranking.
- [src/data_pipeline/README.md](src/data_pipeline/README.md): Lecture crawling and data processing.
- [backend/app/core/cache/README.md](backend/app/core/cache/README.md): Redis semantic cache.

---

## Important Environment Variables

Copy `.env.example` to `.env`, then fill in real values.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL/Supabase connection string |
| `JWT_SECRET` | Secret used to sign access/refresh tokens |
| `myAPIKey` | OpenAI API key for LLM/embedding |
| `OPENAI_MODEL` | Main chat model |
| `REDIS_URL` | Redis Stack URL, default `redis://localhost:6379/0` |
| `SEMANTIC_CACHE_ENABLED` | Enable/disable Redis semantic cache |
| `YOUTUBE_API_KEY` | Used when crawling YouTube playlists |
| `PUQ_DATA_DIR` | Transcript/data directory |
| `PUQ_VECTOR_DB_DIR` | ChromaDB directory |
| `PUQ_VIDEOS_DIR` | Video metadata directory |

---

## Chat Request Workflow

```txt
User sends a question
↓
Frontend streams request to /api/v1/chat/stream
↓
Backend stores user message in PostgreSQL
↓
Redis exact/semantic cache lookup
├─ Hit: stream cached response + store assistant message in DB
└─ Miss: call LangGraph workflow
↓
Supervisor routes to an agent
↓
Agent generates response
↓
Store assistant message in DB
↓
Cache in Redis when cacheable
```

---

## Data/RAG Workflow

```txt
YouTube/transcript data
↓
Data pipeline processes content
↓
Chunking + metadata
↓
Embedding into ChromaDB
↓
Runtime retrieval: vector + keyword
↓
Reranker selects best context
↓
Tutor agent generates answer with citations
```

---

## Useful Commands

### Install Python dependencies

```powershell
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

### Run backend

```powershell
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Run frontend

```powershell
npm --prefix frontend install
npm --prefix frontend run dev
```

### Run Redis locally

If Redis is already installed locally:

```powershell
redis-server
```

Or use Docker:

```powershell
docker compose --profile redis up -d redis-stack
```

Local Redis endpoint:

```txt
REDIS_URL=redis://localhost:6379/0
RedisInsight: http://localhost:8001
```

### Run data pipeline

```powershell
python -m src.data_pipeline.data_loader.pipeline
```

### Quick compile check for modified Python files

```powershell
python -m compileall backend/app src
```

---

## Operational Notes

- PostgreSQL is the **source of truth** for users, sessions, and chat history.
- Redis is only a cache; if Redis data is lost, it can be rebuilt from the database via prewarm.
- `artifacts/` stores large runtime data and is usually not fully committed.
- Backend startup prewarms RAG resources and Redis cache in the background.
- Prompts, responses, and UI prioritize Vietnamese.

---

## Benchmark & Evaluation

Full retrieval benchmark pipeline lives in `experiments/`. See [experiments/README.md](experiments/README.md) for setup and reproduction.

### Benchmark results summary

22 configs tested across chunking strategies, embedding models, and rerankers. Winner: **C21** — hybrid search + `timestamp_150_50_raw` chunking + `bge_m3-finetuned-v3` embedding + Jina reranker.

| Config | Chunk strategy | Embedding | Hit@5 | MRR@10 | NDCG@10 |
|---|---|---|---:|---:|---:|
| **C21** | `timestamp_150_50_raw` | `bge_m3-finetuned-v3` | **0.9467** | **0.8085** | **0.6092** |
| C02 | `recursive` | `bge_m3` | 0.8967 | 0.7471 | 0.5205 |
| C19 | `semantic` | `bge_m3-finetuned-v3` | 0.9033 | 0.7387 | 0.5355 |
| C22 | `parent_child_180s_45s` | `bge_m3-finetuned-v3` | 0.9067 | 0.6723 | 0.5494 |

### Detailed evaluation reports

- [End-to-end retrieval benchmark (22 configs)](experiments/docs/evaluation/end_to_end_retrieval.md) — full results table, selection rationale, winner analysis
- [Embedding model comparison (7 models)](experiments/docs/evaluation/embedding.md) — BGE-M3 variants, multilingual-e5-large, halong_embedding
- [Reranker comparison (6 models)](experiments/docs/evaluation/reranker.md) — Jina v2 winner, latency analysis
- [QA quality metrics (BERTScore + RAGAS)](experiments/docs/evaluation/qa_metrics.md) — faithfulness, context precision/recall, answer relevancy
- [Ground truth dataset guide](experiments/docs/data/groundtruth.md) — how the 350-question evaluation set was created
- [**Ablation Study Report**](docs/ablation_report.md) — full 4-stage ablation: embedding → reranker → chunking (E2E) → generation quality. Explains why C21 was selected as production config.

### Verification & Run Logs (Audit Trail)

To verify the authenticity of all metrics presented in the evaluation reports, you can examine the raw benchmark results (`metrics.json` and `eval_results.json`) generated under `experiments/runs/`:

* **Embedding Benchmarks (`embedding.md`)**:
  * Fine-tuned V3 (Raw): `experiments/runs/embedding/recursive/experiments-runs-finetune-embedding-20260616-120132/20260628T153959Z_be65f4988205/`
  * Other models: Check subfolders inside `experiments/runs/embedding/` or `experiments/runs/hybrid/`.
* **Reranker Benchmarks (`reranker.md`)**:
  * Raw runs are stored in `experiments/runs/reranker/recursive/20260615T185033Z/` (under individual model folders).
* **End-to-End Retrieval (`end_to_end_retrieval.md`)**:
  * Results for each of the 22 configurations (C01 to C22) are archived under `experiments/runs/e2e_reranked/C01/` through `experiments/runs/e2e_reranked/C22/`.
  * E.g., Winner config C21 logs: `experiments/runs/e2e_reranked/C21/metrics.json`.
* **QA Quality Benchmarks (`qa_metrics.md`)**:
  * Generation logs and RAGAS score inputs: `experiments/runs/qa_metrics/`.

### Reproduce benchmarks

```powershell
# Build ChromaDB index
python experiments/scripts/build_index.py --config experiments/configs/index/<config>.yaml

# Run end-to-end retrieval benchmark
python experiments/scripts/benchmark_end_to_end_retrieval.py

# Run embedding benchmark
python experiments/scripts/benchmark_embeddings.py --config experiments/configs/embedding/<config>.yaml

# Run reranker benchmark
python experiments/scripts/benchmark_rerankers.py

# Run QA quality benchmark (BERTScore + RAGAS)
python experiments/scripts/benchmark_qa_metrics.py
```

Outputs go to `experiments/runs/`.

---

## Related Upgrade Documentation

- [Redis plan](docs/upgrade_system/redis.md)
- [Redis architecture](docs/upgrade_system/redis_architecture.md)
- [Deployment notes](DEPLOYMENT.md)
- [Agent rules](AGENTS.md)
- [Fine-tuned Embedding Model Card](models/bge-m3-finetuned/MODEL_CARD.md) — training details, dataset, hyperparameters, evaluation results for `bge-m3-finetuned-v3`
