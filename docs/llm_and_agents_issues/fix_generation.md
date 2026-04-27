# Cập nhật fix routing tool-call cho Quiz Agent
# Đã fix 15/04/2026 : vấn đề thiếu state tool_calls dẫn tới quiz agent không nhận payload đúng, rơi vào direct.
## Triệu chứng
- Khi hỏi kiểu: `tạo quiz cnn`, LLM có thể trả về:
```json
{ "tool": "GenerateQuiz", "arguments": { "topic": "CNN", "num_questions": 5, "difficulty": "medium" } }
```
- Supervisor không nhận ra format này, nên không route sang node `quiz` và có thể rơi về `direct`.

## Root cause
1. `node_supervisor` trước đó chỉ parse format `{"tool_call": {...}}`.
2. `node_quiz` chỉ ưu tiên `args.query`, chưa xử lý tốt payload dạng `arguments` với `topic/num_questions/difficulty`.
3. Wrapper agents (coding/math) phụ thuộc `last_message.tool_calls`, dễ hụt dữ liệu khi tool call nằm ở `state.tool_calls`.
4. `State` chưa khai báo trường `tool_calls`, nên khi chạy qua LangGraph key này bị rơi trong flow thật (đặc biệt thấy rõ khi test qua Streamlit/API), dẫn tới router vẫn chọn `direct`.

## Đã sửa

### 1) Chuẩn hóa payload tool-call ở Supervisor
**File:** `src/rag_core/lang_graph_rag.py`
- Thêm `_normalize_tool_call_payload(parsed)` để hỗ trợ các format:
  - `tool_call`
  - `tool_calls`
  - `tool` + `arguments`
- Luôn trả về chuẩn nội bộ:
```python
{"name": "<ToolName>", "args": {...}}
```
- `node_supervisor` bơm tool calls vào `state.tool_calls` để router và downstream nodes dùng ổn định.

### 2) Đọc args ổn định từ state cho wrappers
**File:** `src/rag_core/lang_graph_rag.py`
- Thêm `_extract_tool_args_from_state(state, tool_name)`.
- `node_coding_wrapper` và `node_math_wrapper` chuyển sang đọc từ `state.tool_calls` (fallback `last_message.tool_calls`).

### 3) Làm quiz agent tương thích payload mới
**File:** `src/rag_core/agents/quiz.py`
- Ưu tiên đọc tool args từ `state.tool_calls`.
- Nếu không có `query`, tự dựng query từ:
  - `topic`
  - `num_questions`
  - `difficulty`
- Ví dụ dựng thành chuỗi kiểu: `Tạo quiz về CNN, 5 câu, độ khó medium`.

### 4) Giữ `tool_calls` trong graph state
**File:** `src/rag_core/state.py`
- Bổ sung field:
```python
tool_calls: list[dict] = []
```
- Mục đích: đảm bảo dữ liệu tool-call survive qua node `supervisor` → `router` trong runtime thật.

## Regression tests đã thêm
**File:** `tests/rag_core/test_lang_graph_rag.py`
- Test case mô phỏng đúng payload lỗi:
```json
{"tool": "GenerateQuiz", "arguments": {"topic":"CNN","num_questions":5,"difficulty":"medium"}}
```
- Kỳ vọng: `node_supervisor` phải xuất `tool_calls[0].name == "GenerateQuiz"` và giữ đúng args.
- Test workflow-level: dựng graph tối giản (`supervisor -> router -> quiz/direct`) và assert payload trên phải route vào `quiz` (không phải `direct`).

## Kết quả
- Luồng tạo quiz với payload `tool + arguments` đã route đúng sang node `quiz`.
- Tránh rơi nhánh `direct` khi LLM trả về format tool-call mới.
