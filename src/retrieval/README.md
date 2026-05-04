# retrieval — Search & Reranking

`src/retrieval/` chứa các thành phần truy hồi context cho Tutor/RAG agent. Mục tiêu là tìm đúng đoạn transcript/chunk liên quan nhất trước khi đưa vào LLM.

---

## Luồng retrieval

```txt
User query
  ↓
Vector search từ ChromaDB
  +
Keyword/BM25 search
  ↓
Hybrid merge candidates
  ↓
CrossEncoder reranker
  ↓
Top context docs cho Tutor agent
```

---

## Cấu trúc

```txt
retrieval/
├── hybrid_search.py       # Kết hợp vector + keyword search
├── keyword_search.py      # BM25/keyword retriever
├── reranking.py           # BGE CrossEncoder reranker
└── text_splitters/        # Logic chia chunk văn bản
```

---

## Khi nào sửa module này?

- Muốn cải thiện chất lượng context/citation.
- Muốn thay threshold, top-k hoặc cách merge kết quả.
- Muốn đổi reranker model.
- Muốn đổi chunking strategy cho transcript.

---

## Lưu ý

- Retrieval ảnh hưởng trực tiếp độ đúng của Tutor agent.
- Đừng chỉ tối ưu latency nếu làm giảm citation quality.
- Nếu sửa output shape của docs, kiểm tra backend stream context và frontend citation rendering.
