# agents — Specialized AI Workers

`src/rag_core/agents/` chứa các agent chuyên trách được Supervisor gọi trong LangGraph workflow.

---

## Các agent chính

| File | Vai trò |
|---|---|
| `tutor.py` | Trả lời kiến thức bài giảng bằng RAG/context/citation |
| `coding.py` | Hỗ trợ lập trình, có thể chạy code sandbox và tự sửa lỗi |
| `coding_retrieval.py` | Retrieval hỗ trợ riêng cho coding nếu cần |
| `math.py` | Giải toán bằng SymPy rồi diễn giải từng bước |
| `quiz.py` | Tạo quiz/trắc nghiệm từ nội dung bài học |
| `direct.py` | Trả lời xã giao hoặc câu hỏi tổng quát |

---

## Contract với graph/backend

Agent nên trả response dạng dict:

```python
{
    "text": "Markdown tiếng Việt",
    "type": "rag" | "coding" | "math" | "direct",
    "video_url": []
}
```

Backend sẽ lưu `text` vào DB và có thể lưu toàn bộ dict vào `metadata_json`.

---

## Lưu ý

- Prompt đã được tối ưu, tránh rewrite lớn nếu chỉ sửa bug nhỏ.
- Coding/math agent có tool execution, cần guard an toàn.
- Nếu thêm field response mới, cập nhật frontend types/renderer nếu cần.
