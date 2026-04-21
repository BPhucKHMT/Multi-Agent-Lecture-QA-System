# AGENTS.md — Hướng dẫn cho AI Agent làm việc với dự án RAG QABot

> Tài liệu này mô tả kiến trúc, quy ước, và hướng dẫn cho các AI coding agent (Copilot, Gemini, Claude, v.v.) khi đọc hiểu và chỉnh sửa codebase.

---

Khi thực hiện bất kì plan trong docs nào cũng phải update lại kết quả đã thực hiện vào đúng phần docs đó.
Ví dụ: nếu đang làm plan trong `Change_Generation.md` thì sau khi hoàn thành mỗi checklist item, phải cập nhật vào phần `Checklist triển khai` trong file đó. Không cập nhật vào đây.




## 📌 Tổng quan dự án

**RAG QABot** (PUQ Q&A) là hệ thống hỏi đáp tự động cho các môn học tại UIT, sử dụng kiến trúc **Retrieval-Augmented Generation (RAG)**. Hệ thống crawl dữ liệu từ playlist YouTube (transcript bài giảng), xử lý ngôn ngữ tự nhiên, tìm kiếm ngữ nghĩa và trả lời kèm trích dẫn nguồn video có timestamp.

- **Ngôn ngữ chính**: Python 3.12+
- **Frontend**: Streamlit (`app.py`)
- **Backend**: FastAPI (`server.py`)
- **LLM**: Google Gemini 2.5 Flash (qua LangChain)
- **Vector DB**: ChromaDB (persist tại `database_semantic/`)
- **Embedding**: BAAI/bge-m3 (HuggingFace)
- **Reranker**: BAAI/bge-reranker-base (CrossEncoder)
- **Orchestration**: LangGraph (state machine workflow)
- **Ngôn ngữ giao tiếp**: Tiếng Việt (comments, prompts, UI)

---

## 🏗️ Kiến trúc hệ thống

```
User (Browser)
    │
    ▼
┌──────────────────┐       HTTP POST /chat       ┌──────────────────────┐
│   Streamlit UI   │ ──────────────────────────▶  │   FastAPI Backend    │
│   (app.py)       │ ◀──────────────────────────  │   (server.py)       │
└──────────────────┘       JSON response          └─────────┬────────────┘
                                                            │
                                                            ▼
                                                  ┌──────────────────────┐
                                                  │   LangGraph Agent    │
                                                  │ (rag/lang_graph_rag) │
                                                  └─────────┬────────────┘
                                                            │
                                              ┌─────────────┼─────────────┐
                                              ▼                           ▼
                                    ┌──────────────┐            ┌──────────────┐
                                    │ Direct Answer│            │  RAG Chain   │
                                    │ (no retrieval│            │ (offline_rag)│
                                    └──────────────┘            └──────┬───────┘
                                                                       │
                                                          ┌────────────┼────────────┐
                                                          ▼            ▼            ▼
                                                    ┌──────────┐ ┌──────────┐ ┌──────────┐
                                                    │ Hybrid   │ │ Reranker │ │   LLM    │
                                                    │ Search   │ │ (Cross-  │ │ (Gemini) │
                                                    │ BM25+MMR │ │ Encoder) │ │          │
                                                    └──────────┘ └──────────┘ └──────────┘
                                                          │
                                                    ┌─────┴─────┐
                                                    ▼           ▼
                                              ┌──────────┐ ┌──────────┐
                                              │ ChromaDB │ │   BM25   │
                                              │ (Vector) │ │(Keyword) │
                                              └──────────┘ └──────────┘
```

### LangGraph Workflow (3 nodes)

```
START → [agent] → (route_decision) → [direct] → END
                                    → [rag]    → END
```

1. **`agent`**: LLM quyết định câu hỏi cần RAG hay trả lời trực tiếp (via tool binding `Retrieve`)
2. **`direct`**: Trả lời trực tiếp không cần retrieval (chào hỏi, câu hỏi chung)
3. **`rag`**: Chạy full pipeline: Hybrid Search → Reranking → LLM Generation với context

---

## 📂 Cấu trúc thư mục & trách nhiệm module

```
final_project/
├── app.py                          # Streamlit frontend — UI chat, render citations
├── server.py                       # FastAPI backend — API /chat, in-memory conversation store
├── config.yaml                     # Danh sách playlist YouTube & cấu hình crawling
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Docker image (Python 3.12)
├── docker-compose.yaml             # Multi-container: FastAPI + Streamlit + MongoDB
├── .env.example                    # Template biến môi trường
│
├── rag/                            # 🧠 Logic chính RAG
│   ├── lang_graph_rag.py           # LangGraph workflow (agent → direct/rag)
│   └── offline_rag.py              # RAG chain: retriever → reranker → LLM prompt → JSON output
│
├── generation/                     # 🤖 LLM configuration
│   └── llm_model.py                # get_llm() — Gemini 2.5 Flash via LangChain
│
├── retriever/                      # 🔍 Retrieval components
│   ├── hybrid_search.py            # EnsembleRetriever (BM25 + Vector, weights 0.5/0.5)
│   ├── keyword_search.py           # BM25 keyword search
│   └── reranking.py                # CrossEncoder reranker (BAAI/bge-reranker-base)
│
├── src/storage/                    # 📦 Vector DB management
│   └── vectorstore.py              # ChromaDB wrapper (BAAI/bge-m3 embeddings, MMR search)
│
├── text_splitters/                 # ✂️ Text chunking
│   └── semantic.py                 # SemanticChunker (OpenAI embeddings, percentile breakpoint)
│
├── data_loader/                    # 📥 Data ingestion pipeline
│   ├── pipeline.py                 # End-to-end: crawl → preprocess → chunk → embed
│   ├── coordinator.py              # YouTube playlist coordinator
│   ├── youtube_fetchers.py         # YouTube transcript/metadata fetching
│   ├── file_loader.py              # File I/O utilities
│   └── preprocess.py               # Text preprocessing
│
├── preprocess/                     # 🧹 Text cleaning
│   └── preprocess.py               # Vietnamese text normalization (pyvi)
│
├── artifacts/                      # 🗂️ Runtime artifacts (ngoài src)
│   ├── data/                       # Raw/processed data
│   ├── chunks/                     # Cached text chunks (JSON)
│   ├── database_semantic/          # ChromaDB persistent storage (chroma.sqlite3)
│   ├── data_extraction/            # Video keyframe/scene extraction output
│   │   ├── Keyframes/
│   │   ├── OCR/
│   │   └── TransNetV2/
│   ├── videos/                     # Downloaded video files
│   └── saved_conversations/        # (Legacy) Local conversation storage
│
├── notebook_baseline/              # 📊 Jupyter notebooks (evaluation, baseline)
└── report/                         # Project report/documentation
```

> Quy ước quan trọng: `src/` chỉ chứa code. Runtime artifacts được gom dưới `artifacts/` và giữ ngoài `src`.

---

## 🔑 Biến môi trường (`.env`)

| Biến | Mục đích |
|------|----------|
| `googleAPIKey` | Google Gemini API key (bắt buộc — dùng cho LLM) |
| `myAPIKey` | OpenAI API key (dùng cho text-embedding-3-large trong chunking) |
| `YOUTUBE_API_KEY` | YouTube Data API v3 key (dùng khi crawl playlist mới) |
| `mongodb_url` | MongoDB connection string (dùng trong production deployment) |
| `PUQ_DATA_DIR` | Override thư mục dữ liệu transcript (mặc định `artifacts/data`) |
| `PUQ_CHUNKS_DIR` | Override thư mục chunk output (mặc định `artifacts/chunks`) |
| `PUQ_VECTOR_DB_DIR` | Override thư mục Chroma persist (mặc định `artifacts/database_semantic`) |
| `PUQ_VIDEOS_DIR` | Override thư mục video tải về (mặc định `artifacts/videos`) |
| `PUQ_DATA_EXTRACTION_DIR` | Override thư mục output data extraction (mặc định `artifacts/data_extraction`) |

---

## ⚙️ Quy ước code

### Ngôn ngữ & phong cách
- **Comments và docstrings**: Viết bằng **tiếng Việt**
- **Tên biến/hàm**: Tiếng Anh, snake_case
- **Tên class**: PascalCase
- **Import style**: Absolute imports (`from rag.lang_graph_rag import call_agent`)
- **Type hints**: Sử dụng (không bắt buộc 100% coverage)

### Format response từ RAG
Response object từ RAG pipeline luôn có cấu trúc sau:
```python
{
    "text": str,              # Nội dung câu trả lời (Markdown, có citation [0], [1], ...)
    "video_url": List[str],   # URL YouTube tương ứng
    "title": List[str],       # Tiêu đề video
    "filename": List[str],    # Tên file transcript gốc
    "start_timestamp": List[str],  # HH:MM:SS
    "end_timestamp": List[str],    # HH:MM:SS
    "confidence": List[str],       # "high" | "medium" | "low" | "zero"
    "type": str               # "rag" | "direct" | "error"
}
```
> ⚠️ Tất cả các mảng (video_url, title, filename, start_timestamp, end_timestamp, confidence) **PHẢI cùng độ dài** và tương ứng theo index.

### Citation Remapping
Khi LLM trả lời, citation `[X]` trong text phải được **remap** để khớp index với mảng `video_url` (chỉ chứa video đã được trích dẫn, không phải tất cả context docs).

---

## 🧪 Cách chạy & test

### Chạy development
```bash
# Terminal 1 — Backend
uvicorn server:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend
streamlit run app.py
```

### Chạy RAG module độc lập
```bash
python -m rag.main
```

### Cập nhật knowledge base (crawl thêm playlist)
```bash
# Chỉnh config.yaml → thêm playlist URL
python -m data_loader.pipeline
```

### Docker
```bash
docker-compose up --build
```

---

## ⚠️ Lưu ý khi chỉnh sửa

### Không nên thay đổi
- **`database_semantic/`**: Đây là ChromaDB persistent storage (~25MB). Không xóa trừ khi rebuild toàn bộ.
- **Response format**: Thay đổi cấu trúc JSON response sẽ ảnh hưởng đến cả `offline_rag.py` (prompt), `lang_graph_rag.py` (parsing), `server.py` (forwarding), và `app.py` (rendering).
- **Prompt trong `offline_rag.py`**: Prompt này đã được tinh chỉnh kỹ để đảm bảo LLM output JSON hợp lệ với citation remapping chính xác. Thay đổi cần test kỹ.

### Cần lưu ý
- **LangGraph state schema** (`State` class trong `lang_graph_rag.py`): Thay đổi sẽ ảnh hưởng tất cả nodes.
- **Embedding model** (`BAAI/bge-m3`): Thay đổi embedding model yêu cầu rebuild toàn bộ vector store.
- **Reranker filtering**: `CrossEncoderReranker` có `BAD_HINTS` để lọc nội dung quảng cáo YouTube.
- **CORS**: Hiện đang cho phép tất cả origins (`*`). Cần restrict trong production.

### Dependencies quan trọng
- `langchain==0.3.27` + `langgraph` — Orchestration framework
- `chromadb==1.3.2` — Vector database
- `sentence-transformers==5.1.2` — Embedding models
- `torch` — Backend cho models (hỗ trợ CUDA)
- `langchain-google-genai==2.1.12` — Gemini integration

---

## 🔧 Patterns thường gặp

### Thêm retriever mới
1. Tạo file trong `retriever/`, implement class với method `get_retriever()`
2. Tích hợp vào `HybridSearch` hoặc thay thế trong `build_rag_chain()` (`lang_graph_rag.py`)

### Thêm LLM model mới
1. Sửa `generation/llm_model.py` — thêm function mới hoặc sửa `get_llm()`
2. LLM phải compatible với LangChain interface (`BaseChatModel`)

### Thêm data source mới (ngoài YouTube)
1. Tạo fetcher mới trong `data_loader/`
2. Output phải tuân theo format: `{"full_text", "position_map", "playlist", "filename", "title", "url"}`
3. Chạy qua `text_splitters/semantic.py` để chunk
4. Load vào ChromaDB qua `src/storage/vectorstore.py`

### Thêm node mới vào LangGraph
1. Define node function trong `rag/lang_graph_rag.py`
2. Register vào `StateGraph` và thêm edges
3. Đảm bảo output node cuối set `response` field trong `State`

---

## 📊 Hiệu năng & giới hạn

- **RAM**: Backend + embedding models cần ~4GB
- **GPU**: Optional (CUDA) — reranker và embedding có thể chạy trên CPU
- **Concurrent users**: Thiết kế cho ~50 users đồng thời
- **Vector DB size**: ~25MB (ChromaDB SQLite)
- **Response time**: Phụ thuộc Gemini API latency (~5-15s/query)
- **Request timeout**: Frontend timeout 360s cho mỗi request

---

## 📁 Files quan trọng nhất (ưu tiên đọc)

1. `rag/lang_graph_rag.py` — Entry point của RAG pipeline, LangGraph workflow
2. `rag/offline_rag.py` — Core RAG chain với prompt engineering
3. `server.py` — Backend API endpoints
4. `app.py` — Frontend UI và response rendering
5. `src/storage/vectorstore.py` — Vector DB configuration
6. `retriever/reranking.py` — Reranking logic
7. `data_loader/pipeline.py` — Data ingestion pipeline



# 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
