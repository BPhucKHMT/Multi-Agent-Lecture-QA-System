# rag_core — LangGraph Multi-Agent Workflow

`src/rag_core/` là trung tâm điều phối AI của hệ thống. Module này định nghĩa graph LangGraph, supervisor routing, state dùng chung, các agent chuyên trách và tools hỗ trợ.

---

## Vai trò

```txt
backend chat service
  ↓
workflow.astream_events(initial_state)
  ↓
Supervisor
  ↓
Specialized agent
  ↓
Final response JSON
```

Backend dùng stream events từ graph để gửi status/token/context về frontend.

---

## Cấu trúc

```txt
rag_core/
├── lang_graph_rag.py      # Graph chính + supervisor node + routing
├── state.py               # State schema dùng trong graph
├── resource_manager.py    # Prewarm/cache resource nặng
├── router_patterns.py     # Deterministic steering patterns
├── offline_rag.py         # Flow RAG offline/legacy nếu cần
├── agents/
│   ├── tutor.py           # Agent RAG kiến thức bài giảng
│   ├── coding.py          # Agent lập trình + self-correction
│   ├── math.py            # Agent toán + SymPy
│   ├── quiz.py            # Agent tạo trắc nghiệm
│   └── direct.py          # Agent trả lời trực tiếp
└── tools/
    └── sandbox.py         # Sandbox chạy code an toàn tương đối
```

---

## Agent routing

Supervisor quyết định agent theo intent:

| Agent | Khi nào dùng |
|---|---|
| `Tutor` | Hỏi kiến thức bài giảng, cần RAG/citation |
| `Coding` | Hỏi code, debug, thuật toán, chạy snippet |
| `Math` | Bài toán công thức, đại số, giải tích, xác suất |
| `Quiz` | Yêu cầu tạo câu hỏi/trắc nghiệm |
| `Direct` | Chào hỏi, câu hỏi tổng quát không cần retrieval |

Ngoài LLM tool-calling, `router_patterns.py` có deterministic steering để route nhanh các pattern rõ ràng.

---

## Response contract

Các agent nên trả dict có dạng gần như:

```python
{
    "text": "Nội dung Markdown tiếng Việt",
    "video_url": ["https://..."],
    "type": "rag" | "direct" | "coding" | "math"
}
```

Backend sẽ lấy response này để:

1. stream metadata về frontend;
2. lưu assistant message vào PostgreSQL;
3. ghi Redis semantic cache nếu response cacheable.

---

## Lưu ý khi chỉnh sửa

- `state.py` ảnh hưởng toàn bộ graph, sửa phải rất cẩn thận.
- Prompt trong `agents/` đã tối ưu tiếng Việt, không rewrite lớn nếu không cần.
- Nếu thêm agent mới, cần cập nhật `lang_graph_rag.py`, routing và docs.
- Coding/math agent có thể chạy tool/sandbox, cần giữ guard an toàn.
