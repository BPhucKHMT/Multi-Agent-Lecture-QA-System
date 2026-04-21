# Copilot Instructions for PUQ RAG QABot

## Build, run, and test commands

```bash
pip install -r requirements.txt
```

```bash
# Backend API
uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload

# Frontend
streamlit run src/frontend/app.py
```

```bash
# Docker (backend + frontend)
docker-compose up --build
```

```bash
# Data ingestion/indexing pipeline
python -m src.data_pipeline.data_loader.pipeline
```

```bash
# Full test suite
pytest -q tests

# Run one test file
pytest -q tests\rag_core\test_lang_graph_rag.py

# Run one test case
pytest -q tests\rag_core\test_lang_graph_rag.py::test_workflow_routes_quiz_from_supervisor_agent_tool_step
```

No repository-wide lint command is currently configured (`ruff`, `flake8`, `mypy`, etc. are not set up in project config files).

## High-level architecture

The runtime path is:

1. `src/frontend/app.py` sends chat requests to FastAPI (`/chat` and `/chat/stream`).
2. `src/api/router.py` routes requests to `src/api/services/chat_service.py`.
3. `chat_service.py` keeps in-memory conversation state and calls `src.rag_core.lang_graph_rag.call_agent(...)`.
4. `src/rag_core/lang_graph_rag.py` runs a LangGraph workflow:
   - `supervisor` node uses `create_tool_calling_agent(...)` + `AgentExecutor(...)`.
   - Router dispatches to one of: `tutor`, `quiz`, `coding`, `math`, or `direct`.
5. Retrieval-heavy paths:
   - `tutor` uses `Offline_RAG` (`src/rag_core/offline_rag.py`) with hybrid retrieval + reranking.
   - `quiz` retrieves/reranks context, then generates structured quiz output.
6. Shared heavy resources are centralized in `src/rag_core/resource_manager.py` (VectorDB/retrievers/rerankers/chains), not re-initialized per call.

Separate from online chat runtime, ingestion is under `src/data_pipeline/` and ends by indexing chunks into Chroma via `src/storage/vectorstore.py`.

## Key repository conventions

- Keep runtime code under `src/`; runtime data/artifacts belong under `artifacts/` (path overrides via `PUQ_*` env vars and `src/shared/config.py`).
- Use absolute imports from `src...` modules.
- Comments/docstrings/prompts/UI text are Vietnamese; identifiers remain English (`snake_case`/`PascalCase`).
- Response payload contract is strict across agents and UI:
  - Keep keys consistent (`text`, `video_url`, `title`, `filename`, `start_timestamp`, `end_timestamp`, `confidence`, `type`).
  - Metadata arrays must stay index-aligned and same length.
  - Citation indices in `text` (`[0]`, `[1]`, ...) are consumed by frontend link rendering in `src/frontend/app.py`.
- In current supervisor design (`src/rag_core/lang_graph_rag.py`), routing is single-route/single-tool-per-turn (router uses first tool call).
- When implementing tasks from docs plans, update progress back into the same docs plan file (per `AGENTS.md`).
