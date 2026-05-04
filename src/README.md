# src — AI/RAG Engine

`src/` chứa lõi AI của PUQ Q&A: LangGraph multi-agent workflow, retrieval pipeline, vectorstore, LLM factory và data ingestion. Backend FastAPI trong `backend/` gọi vào module này để tạo câu trả lời.

---

## Vai trò

```txt
backend/app/services/chat.py
  ↓
src.rag_core.lang_graph_rag.workflow
  ↓
Supervisor route agent
  ↓
Tutor / Coding / Math / Quiz / Direct
  ↓
Retrieval + LLM + tools
```

---

## Cấu trúc thư mục

```txt
src/
├── rag_core/       # LangGraph workflow, supervisor, agents, tools, state
├── retrieval/      # Hybrid search, keyword BM25, reranker, text splitters
├── storage/        # ChromaDB/vectorstore wrapper
├── generation/     # LLM factory và model config
├── data_pipeline/  # Crawl/load/preprocess/chunk dữ liệu bài giảng
├── api/            # Legacy/API helpers nếu còn dùng
├── shared/         # Shared utilities
└── notebook_baseline/ # Tài liệu/hình ảnh baseline nghiên cứu
```

---

## Module quan trọng

| File/thư mục | Mục đích |
|---|---|
| `rag_core/lang_graph_rag.py` | Định nghĩa LangGraph supervisor workflow |
| `rag_core/agents/` | Logic các agent chuyên trách |
| `rag_core/resource_manager.py` | Prewarm embedding/vector DB/reranker |
| `rag_core/router_patterns.py` | Pattern steering cho supervisor |
| `retrieval/hybrid_search.py` | Kết hợp vector search và keyword search |
| `retrieval/reranking.py` | CrossEncoder reranking |
| `storage/vectorstore.py` | Quản lý ChromaDB persistent store |
| `generation/llm_model.py` | Khởi tạo ChatOpenAI |
| `data_pipeline/` | Tạo dữ liệu cho RAG từ transcript/video |

---

## Chạy/kiểm tra nhanh

Cài dependencies từ root:

```powershell
pip install -r requirements.txt
```

Chạy data pipeline khi cần cập nhật dữ liệu:

```powershell
python -m src.data_pipeline.pipeline
```

Compile nhanh module AI:

```powershell
python -m compileall src
```

---

## Runtime data

`src/` không nên lưu runtime data lớn. Dữ liệu được lưu ở root `artifacts/`:

```txt
artifacts/
├── data/               # Transcript/raw/processed content
├── chunks/             # Cached chunks
├── database_semantic/  # ChromaDB persistent vector database
└── videos/             # Metadata + thumbnails video
```

---

## Agent workflow

```txt
User message
  ↓
Supervisor
  ├─ Tutor: RAG kiến thức bài giảng
  ├─ Coding: hỗ trợ lập trình, sandbox/self-correction
  ├─ Math: SymPy + diễn giải LaTeX
  ├─ Quiz: tạo câu hỏi kiểm tra
  └─ Direct: chào hỏi/câu hỏi tổng quát
```

---

## Quy ước khi sửa `src/`

- Prompt và câu trả lời ưu tiên tiếng Việt.
- Comments/docstrings viết tiếng Việt.
- Không thay đổi `rag_core/state.py` nếu chưa kiểm tra toàn bộ workflow.
- Nếu sửa retrieval, kiểm tra citation và response streaming ở backend/frontend.
- Nếu sửa data pipeline, đảm bảo `artifacts/` và ChromaDB vẫn tương thích.
