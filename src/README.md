# src — AI/RAG Engine

`src/` chứa lõi AI của PUQ Q&A: LangGraph multi-agent workflow, retrieval pipeline, vectorstore, LLM factory và data ingestion. Backend FastAPI trong `backend/` gọi vào module này để tạo câu trả lời.

---

## Cấu trúc thư mục chi tiết

```txt
src/
├── __init__.py
├── rag_core/                        # LangGraph workflow, supervisor, agents, tools
│   ├── __init__.py
│   ├── lang_graph_rag.py            # Graph chính + supervisor node + routing
│   ├── state.py                     # State schema dùng trong graph
│   ├── resource_manager.py          # Prewarm/cache resource nặng (embedding, reranker)
│   ├── router_patterns.py           # Deterministic steering patterns cho supervisor
│   ├── offline_rag.py               # Flow RAG offline/legacy
│   ├── utils.py                     # Utilities
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── tutor.py                 # Agent RAG: trả lời từ kiến thức bài giảng + citation
│   │   ├── coding.py                # Agent lập trình: sinh/chạy/tự sửa code trong sandbox
│   │   ├── coding_retrieval.py      # Retrieval helper riêng cho coding agent
│   │   ├── math.py                  # Agent toán: SymPy + LaTeX step-by-step
│   │   ├── quiz.py                  # Agent quiz: tạo câu hỏi trắc nghiệm
│   │   ├── direct.py                # Agent direct: chào hỏi, câu hỏi tổng quát
│   │   ├── coding.py.bak            # Backup coding.py
│   │   ├── coding.py.bak.21_04_2026 # Backup coding.py (21/04/2026)
│   │   ├── math.py.bak              # Backup math.py
│   │   ├── math.py.bak.21_04_2026   # Backup math.py (21/04/2026)
│   │   ├── quiz.py.bak              # Backup quiz.py
│   │   ├── quiz.py.bak.21_04_2026   # Backup quiz.py (21/04/2026)
│   │   ├── tutor.py.bak             # Backup tutor.py
│   │   └── tutor.py.bak.21_04_2026  # Backup tutor.py (21/04/2026)
│   └── tools/
│       ├── __init__.py
│       └── sandbox.py               # Sandbox chạy code an toàn cho coding agent
├── retrieval/                       # Hybrid search, BM25, reranker, text splitters
│   ├── __init__.py
│   ├── hybrid_search.py             # Kết hợp vector search + BM25 keyword search
│   ├── keyword_search.py            # BM25 keyword search đơn lẻ
│   ├── keyword_search.py.bak        # Backup keyword_search.py
│   ├── reranking.py                 # CrossEncoder reranking (Jina v2)
│   └── text_splitters/
│       ├── __init__.py
│       ├── chunker.py               # Text chunking strategies
│       └── README.md                # Chi tiết chunking
├── storage/                         # ChromaDB/vectorstore wrapper
│   ├── __init__.py
│   ├── vectorstore.py               # Quản lý ChromaDB persistent store
│   └── README.md
├── generation/                      # LLM factory và model config
│   ├── __init__.py
│   ├── llm_model.py                 # Khởi tạo ChatOpenAI, model config
│   └── README.md
├── data_pipeline/                   # Crawl/load/preprocess/chunk dữ liệu bài giảng
│   ├── __init__.py
│   ├── combine_content.py           # Combine nội dung từ nhiều nguồn
│   ├── README.md
│   └── data_loader/
│       ├── __init__.py
│       ├── coordinator.py           # Pipeline coordinator
│       ├── file_loader.py           # File loading (PDF, DOCX, etc.)
│       ├── keyframe_extractor.py    # Trích xuất keyframe từ video
│       ├── llm_utils.py             # LLM utility helpers
│       ├── ocr_processor.py         # OCR processing (EasyOCR)
│       ├── pipeline.py              # Main pipeline entry point
│       ├── pipeline_state.py        # Pipeline state management
│       ├── preprocess.py            # Preprocessing
│       ├── scene_detector.py        # Scene detection (TransNetV2)
│       ├── utils.py                 # Utilities
│       ├── video_downloader.py      # Video download
│       ├── youtube_fetchers.py      # YouTube transcript fetching
│       └── artifacts/
│           └── data_extraction/
│               └── SceneJSON/       # Scene detection output
├── shared/                          # Shared config và logging
│   ├── __init__.py
│   ├── config.py                    # Shared configuration
│   └── logging.py                   # Shared logging setup
├── api/                             # Legacy/API helpers
│   └── __init__.py
└── notebook_baseline/               # Baseline research notebooks
    ├── architecture.png
    ├── demo1.png
    ├── pipeline.ipynb               # Jupyter notebook pipeline
    ├── pipeline.png
    └── 0.26.0/                      # Versioned artifacts
```

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

## Module quan trọng

| File/thư mục | Mục đích |
|---|---|
| `rag_core/lang_graph_rag.py` | Định nghĩa LangGraph supervisor workflow |
| `rag_core/state.py` | State schema dùng trong graph |
| `rag_core/agents/tutor.py` | Agent RAG kiến thức bài giảng |
| `rag_core/agents/coding.py` | Agent lập trình + self-correction |
| `rag_core/agents/math.py` | Agent toán + SymPy + LaTeX |
| `rag_core/agents/quiz.py` | Agent tạo câu hỏi trắc nghiệm |
| `rag_core/agents/direct.py` | Agent trả lời trực tiếp |
| `rag_core/tools/sandbox.py` | Sandbox chạy code an toàn |
| `rag_core/resource_manager.py` | Prewarm embedding/vector DB/reranker |
| `rag_core/router_patterns.py` | Pattern steering cho supervisor |
| `retrieval/hybrid_search.py` | Kết hợp vector search và keyword search |
| `retrieval/reranking.py` | CrossEncoder reranking |
| `retrieval/text_splitters/chunker.py` | Text chunking strategies |
| `storage/vectorstore.py` | Quản lý ChromaDB persistent store |
| `generation/llm_model.py` | Khởi tạo ChatOpenAI |
| `data_pipeline/` | Tạo dữ liệu cho RAG từ transcript/video |
| `shared/config.py` | Shared configuration |
| `shared/logging.py` | Shared logging setup |

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
├── data/          # Transcript/raw/processed content
├── chunks/        # Cached chunks
├── database_semantic/  # ChromaDB persistent vector database
└── videos/        # Metadata + thumbnails video
```

---

## Quy ước khi sửa `src/`

- Prompt và câu trả lời ưu tiên tiếng Việt.
- Comments/docstrings viết tiếng Việt.
- Không thay đổi `rag_core/state.py` nếu chưa kiểm tra toàn bộ workflow.
- Nếu sửa retrieval, kiểm tra citation và response streaming ở backend/frontend.
- Nếu sửa data pipeline, đảm bảo `artifacts/` và ChromaDB vẫn tương thích.
- File `.bak` là backup từ các lần refactor trước, không sửa trực tiếp.
