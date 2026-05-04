# cache — Redis Semantic Cache

`backend/app/core/cache/` chứa logic cache cho backend, hiện tập trung vào Redis Stack semantic cache dùng cho chat response.

---

## Mục tiêu

- Trả nhanh câu hỏi đã hỏi hoặc câu hỏi rất giống.
- Giảm số lần gọi LangGraph/RAG/LLM.
- Không thay thế PostgreSQL chat history.

---

## Cấu trúc

```txt
cache/
├── semantic.py   # Exact hash + vector search + guard/filter
└── prewarm.py    # Load N cặp Q/A gần nhất từ DB vào Redis khi startup
```

---

## Data model trong Redis

```txt
semantic_cache:exact:{sha256(normalized_question)} -> semantic_cache:item:{uuid}
semantic_cache:item:{uuid} -> HASH
idx:semantic_cache -> RediSearch vector index
```

Một item hash chứa:

- `prompt`: câu hỏi gốc;
- `normalized_prompt`: câu hỏi đã normalize;
- `response_json`: response đầy đủ;
- `response_text`: text để kiểm tra quality;
- `response_type`: `rag`, `direct`, `tutor`;
- `quality_status`: thường là `ok`;
- `cache_scope`: thường là `global`;
- `embedding`: vector float32 binary.

---

## Lookup flow

```txt
Question
  ↓
Normalize + SHA-256 exact key
  ├─ Exact hit: dùng ngay
  └─ Exact miss:
      ↓
    Check query cacheable?
      ↓
    KNN vector search top-k
      ↓
    Với từng candidate:
      - similarity threshold
      - intent guard
      - quality/cache scope
      - keyword overlap nếu chưa đủ strong threshold
      ↓
    Hit hoặc miss
```

---

## Vì sao cần Redis binary client?

Embedding được ghi vào Redis dưới dạng bytes. Nếu dùng client `decode_responses=True`, redis-py có thể cố decode vector binary thành text và lỗi.

Semantic cache phải dùng:

```python
redis.from_url(settings.REDIS_URL, decode_responses=False)
```

---

## Source of truth

PostgreSQL vẫn lưu đầy đủ:

```txt
user question + assistant response + session_id + metadata
```

Redis chỉ là cache. Nếu Redis mất dữ liệu, backend có thể prewarm lại từ DB.
