# retrieval — Hybrid Search, BM25, Reranker, Text Splitters

`src/retrieval/` chứa toàn bộ pipeline retrieval cho RAG: hybrid search (dense vector + BM25 keyword), CrossEncoder reranking, và text chunking strategies.

---

## Cấu trúc

```txt
retrieval/
├── __init__.py
├── hybrid_search.py   # Kết hợp vector search + BM25 keyword search
├── keyword_search.py  # BM25 keyword search đơn lẻ
├── reranking.py       # CrossEncoder reranking
└── text_splitters/
    ├── __init__.py
    ├── chunker.py     # Text chunking strategies
    └── README.md      # Chi tiết chunking
```

---

## Hybrid search

`hybrid_search.py` kết hợp 2 retrieval paths:

1. **Dense (vector)**: ChromaDB similarity search bằng embedding model
2. **Sparse (keyword)**: BM25 over `page_content + OCR text`

Fusion: weighted sum, mặc định `weights=[0.5, 0.5]`.

```python
from src.retrieval.hybrid_search import HybridSearch

hs = HybridSearch(
    chroma_collection=collection,
    bm25_index=bm25_index,
    weights=[0.5, 0.5],
)
results = hs.search(query, top_k=40)
```

---

## Keyword search (BM25)

`keyword_search.py` wrapper BM25Lucene/BM25Okapi. Dùng enriched text (`page_content + OCR`) làm document body.

---

## Reranking

`reranking.py` wrap CrossEncoder model (Jina reranker v2). Input: top-K candidates từ hybrid search → output: ranked top-N.

```python
from src.retrieval.reranking import Reranker

reranker = Reranker(model_name="jina-reranker-v2-base-multilingual")
ranked = reranker.rerank(query, candidates, top_n=10)
```

---

## Text splitters

Xem chi tiết tại [text_splitters/README.md](text_splitters/README.md).

Strategies:

| Strategy | Mô tả |
|---|---|
| `recursive` | Recursive character splitting, mặc định |
| `timestamp_90_30` | Chunk theo transcript timestamp: 90s window, 30s overlap |
| `timestamp_150_50_raw` | 150s window, 50s overlap, raw transcript |
| `semantic` | LLM-based semantic chunking |
| `parent_child_180s_45s` | Parent 180s + child 45s, retrieval dùng child, evaluation dùng parent |

---

## Kết nối với experiments

Config retrieval trong `experiments/configs/embedding/` và `experiments/configs/index/` xác định:
- Strategy chunking
- Embedding model
- Hybrid weights
- Reranker model

Chạy benchmark: `python experiments/scripts/benchmark_end_to_end_retrieval.py`

Kết quả: `experiments/docs/evaluation/end_to_end_retrieval.md`
