# Repository Guidelines

## Project Overview

PUQ RAG QABot answers Vietnamese UIT course questions using lecture/video retrieval and a LangGraph multi-agent supervisor. The application is a FastAPI service (`backend/`), a React/TypeScript SPA (`frontend/`), and a Python RAG/ingestion engine (`src/`). PostgreSQL stores users and conversations; Redis Stack supports token revocation, rate limits, and semantic caching; Chroma stores lecture embeddings.

## Architecture & Data Flow

- `frontend/src/lib/api/chat.ts` posts an access-token-authenticated request to `POST /api/v1/chat/stream` and parses SSE `token`, `status`, `context`, `metadata`, and `error` events.
- `backend/app/api/v1/endpoints/chat.py` injects authentication, SQLAlchemy session, binary Redis client, and rate limiting. `backend/app/services/chat.py` loads/saves PostgreSQL history, checks Redis semantic cache, streams `workflow.astream_events(...)`, and persists the final answer.
- `src/rag_core/lang_graph_rag.py` routes **one tool/agent per turn**: Jev (`src/generation/jev_router.py`) first, GPT-6 Luna tool calling on failure, then a simple fallback. The first tool call selects tutor, quiz, coding, math, or direct. Graph state lives in `src/rag_core/state.py`; coding and math are subgraphs.
- Tutor uses `src/rag_core/offline_rag.py`: query expansion → hybrid Chroma/BM25 retrieval (`src/retrieval/`) → reranking → cited answer. Quiz also retrieves lecture context. `src/rag_core/resource_manager.py` owns shared, lazily initialized heavy retrievers, vector DB, and separate tutor/quiz rerankers; reuse them rather than constructing models per request.
- `src/data_pipeline/data_loader/pipeline.py` ingests playlists, transcripts, and visual content into `artifacts/` and the Chroma index. `config.yaml` selects ingestion settings; `src/shared/config.py:get_path` resolves `PUQ_*` artifact path overrides.

## Key Directories

- `backend/app/`: API v1 routes, Pydantic schemas, auth dependencies, chat service, DB models/cache, and application lifecycle; `backend/alembic/` holds migrations.
- `src/rag_core/`, `src/retrieval/`, `src/generation/`, `src/storage/`: graph/agents, search/reranking, LLM clients, and Chroma access.
- `src/data_pipeline/`: ingestion and indexing; `artifacts/`: generated transcripts, chunks, videos, vector DB, and other runtime data, not source code.
- `frontend/src/`: React routes/components, Context-based conversation state, typed API client, and co-located tests.
- `tests/`: Python unit/API/RAG tests; `scripts/`: live supervisor checks and benchmarks; `experiments/`: offline retrieval/evaluation work; `docs/`: research and implementation plans.

## Development Commands

Run from the repository root unless noted:

```text
pip install -r requirements.txt
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
npm --prefix frontend ci
npm --prefix frontend run dev
python -m src.data_pipeline.data_loader.pipeline
pytest -q tests
pytest -q tests/rag_core/test_lang_graph_rag.py
npm --prefix frontend run test
npm --prefix frontend run build
```

`npm --prefix frontend run build` runs `tsc -b && vite build`. On Windows, `.\dev.ps1 up` starts the CPU API, frontend, Redis, and monitoring with Docker Compose; `.\dev.ps1 up -NoMonitoring` omits monitoring, `-Gpu` selects GPU, and `.\dev.ps1 down` stops the stack. Alternatively: `docker compose --profile cpu --profile frontend up --build`. Apply migrations using `alembic -c backend/alembic.ini upgrade head` when needed. There is no configured repository-wide Python lint or type-check command, nor an npm lint script.

## Code Conventions & Common Patterns

- Python modules in `backend/` and `src/` use absolute imports (`from src.rag_core.state import State`); identifiers use `snake_case`/`PascalCase`. Comments, docstrings, prompts, and user-facing text are Vietnamese. Keep changes scoped and update the affected tests/contracts rather than duplicating an existing pattern.
- FastAPI uses `Depends(...)` for user, SQLAlchemy, Redis, and rate-limit dependencies. Async chat streams emit SSE; synchronous ML initialization/work is offloaded to worker threads so it does not block the event loop. Background prewarm and external integrations log failures explicitly.
- Preserve the shared response contract: `text`, `video_url`, `title`, `filename`, `start_timestamp`, `end_timestamp`, `confidence`, `type` (plus agent-specific data). Citation markers `[0]`, `[1]`, ... in `text` index **equal-length, aligned** metadata arrays consumed by `frontend/src/components/chat/MarkdownRenderer.tsx`.
- Tag final streamed model calls `final_answer` or `final_answer_json`; `backend/app/services/chat.py` filters out untagged/intermediate tokens such as `internal_query`. Use the binary Redis client for vector semantic cache; the text client serves auth/rate-limit operations.
- Frontend state uses React Context and hooks (`frontend/src/store/conversationStore.ts`); chat transport and response normalization live in `frontend/src/lib/api/`. Keep the TypeScript API/SSE contracts aligned with Python responses.
- When implementing a plan in `docs/`, record checklist progress and verification **in that same plan file**, not in this guide.

## Important Files

`backend/app/main.py` (lifespan/API entry), `backend/app/services/chat.py` (stream/cache/history), `backend/app/core/config.py` (service settings), `src/rag_core/lang_graph_rag.py` (routing), `src/rag_core/state.py` (graph contract), `src/rag_core/resource_manager.py` (heavy resources), `src/rag_core/offline_rag.py` (retrieval), `frontend/src/lib/api/chat.ts` (SSE consumer), `frontend/src/store/conversationStore.ts` (UI state), `.env.example` (required configuration), and `docker-compose.yaml`/`dev.ps1` (local stack). See `backend/README.md`, `frontend/README.md`, and `src/README.md` for subsystem detail; verify commands against entry points because some older docs contain obsolete paths.

## Runtime/Tooling Preferences

- Python 3.12 is the CPU Docker base; use `pip` with root `requirements.txt` locally, or the CPU/GPU/runtime/pipeline requirement variants for container targets. Frontend uses Node 22 in Docker and **npm** (`frontend/package-lock.json`; Docker uses `npm ci`), not Bun/Yarn.
- Start from `.env.example`; supply `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, and provider keys for live integrations. Keep secrets out of commits. `PUQ_*` variables redirect runtime artifacts. For host-run Vite, set `VITE_API_PROXY_TARGET=http://localhost:8000` (or `VITE_API_BASE_URL`), since the default proxy hostname resolves only inside Docker.
- `docker-compose.observability.yaml` adds optional Prometheus/Grafana monitoring; `dev.ps1` includes it by default and expects Grafana credentials when monitoring is enabled.

## Testing & QA

- Python: `pytest -q tests` or a targeted file/case, e.g. `pytest -q tests/rag_core/test_lang_graph_rag.py::test_workflow_routes_quiz_from_supervisor_agent_tool_step`. Tests use local `monkeypatch` fixtures, in-memory DB/Redis/LLM fakes, `httpx.MockTransport`, and `asyncio.run(...)` or `@pytest.mark.anyio` for async paths; avoid live provider calls in ordinary unit tests.
- Frontend: `npm --prefix frontend run test` runs co-located Vitest tests; `npm --prefix frontend run build` type-checks and bundles. No configured coverage threshold or repository-wide linter. Live routing smoke/latency scripts in `scripts/` require provider credentials and are separate from the default test suite.
