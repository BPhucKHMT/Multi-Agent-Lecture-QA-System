# Phương pháp Option A cho Supervisor Tool Calling

## 1) Vấn đề quan sát được
- Với yêu cầu kiểu: **"tạo quiz diffusion"**, hệ thống từng có lúc trả về dạng:
  - một đoạn phân tích bằng text tự do (không route đúng node quiz),
  - kèm payload giống tool-call/JSON trong nội dung text.
- Hệ quả: router có thể rơi nhánh `direct` thay vì `quiz`.

## 2) Root cause trong luồng cũ
- Luồng cũ phụ thuộc mạnh vào việc tự đọc/parse nội dung text để suy ra tool call.
- Cách parse thủ công JSON/tool-call dễ vỡ khi format model thay đổi.
- Khi không bóc tách được tool call ổn định, quyết định điều hướng bị sai.

## 3) Phương pháp áp dụng (Option A)
Chuyển sang agent tool-calling chuẩn của LangChain:
- dùng `@tool` để khai báo tool,
- dùng `create_tool_calling_agent(...)`,
- chạy qua `AgentExecutor(..., return_intermediate_steps=True)`,
- **không** dựa vào cơ chế parse JSON/tool-call thủ công như trước.

```python
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent

@tool("GenerateQuiz")
def generate_quiz_tool(query: str = "", topic: str = "") -> str:
    return query or topic

supervisor_agent = create_tool_calling_agent(llm, SUPERVISOR_TOOLS, supervisor_prompt)
supervisor_executor = AgentExecutor(
    agent=supervisor_agent,
    tools=SUPERVISOR_TOOLS,
    return_intermediate_steps=True,
    verbose=False,
)
```

## 4) Ghi chú triển khai chính trong repo này
- **Ưu tiên tool call mới nhất từ `intermediate_steps`:**  
  `src/rag_core/lang_graph_rag.py::_extract_tool_calls_from_intermediate_steps` chuẩn hóa rồi `reversed(...)`, để router lấy step mới nhất trước.
- **Mapping `tool_input` dạng string → `{"query": ...}`:**  
  `src/rag_core/lang_graph_rag.py::_coerce_tool_args` xử lý trường hợp action trả chuỗi thuần.
- **Routing sang `GenerateQuiz`:**  
  `src/rag_core/lang_graph_rag.py::router` map `name == "GenerateQuiz"` thành nhánh `"quiz"`.

## 5) Bằng chứng test (targeted)
- Lệnh:
  ```bash
  python -m pytest tests\rag_core\test_lang_graph_rag.py tests\api\test_chat_stream.py -q
  ```
- Kết quả:
  - `15 passed`
- Nhóm kiểm chứng chính:
  - trích xuất tool call từ `intermediate_steps`,
  - ưu tiên latest tool call,
  - map string `tool_input` sang `query`,
  - route đúng sang quiz.

## 6) Quy trình review tự động bằng sub-agent
- Đã chạy vòng review tự động theo 2 lớp:
  1. **Spec review**: xác nhận implementation bám đúng Option A (`@tool` + `create_tool_calling_agent`).
  2. **Code-quality review**: kiểm tra lỗi logic có ảnh hưởng hành vi (stale tool call, mất `query` từ string input).
- Các góp ý quan trọng đã được fix trước khi chốt.
- Artifact review trong phiên:
  - `spec-review-option-a-fixes` (PASS)
  - `quality-review-option-a-fixes` (APPROVED)

## 7) Hạn chế / lưu ý
- Hiện tại vẫn phụ thuộc vào chất lượng quyết định tool của model ở tầng supervisor.  
- Nếu model chọn sai tool ngay từ đầu, router vẫn đi theo tool đó (dù cơ chế parse/điều hướng đã ổn định hơn nhiều so với cách parse JSON thủ công).
