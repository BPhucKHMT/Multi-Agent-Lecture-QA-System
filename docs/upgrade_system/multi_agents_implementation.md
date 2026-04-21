# Kế Hoạch Triển Khai Kiến Trúc Đa Đặc Vụ (Multi-Agent Architecture)

> **Dành cho Claude:** YÊU CẦU SUB-SKILL: Sử dụng superpowers:executing-plans để thực thi kế hoạch này từng bước một.

**Mục tiêu:** Tái cấu trúc hệ thống RAG (hiện chỉ có 1 agent) thành một kiến trúc đa đặc vụ do Supervisor điều phối trong Chatspace, với các sub-graphs chuyên dụng cho việc viết code, giải toán, và tạo câu hỏi trắc nghiệm (quiz).

**Kiến trúc:** Chúng ta sẽ thay thế hệ thống LangGraph hiện tại bằng một hệ thống Supervisor agent có nhiệm vụ điều hướng các yêu cầu đến các sub-agents chuyên biệt. Các agents đơn giản (Tutor, Quiz) sẽ được triển khai dưới dạng tool calls trực tiếp. Các agents phức tạp (Coding, Math) sẽ được triển khai dưới dạng LangGraph sub-graphs với các vòng lặp tự xác minh và sửa lỗi nội bộ. Chúng ta cũng sẽ xây dựng một sandbox thực thi code cục bộ an toàn dùng chung cho Coding và Math agents.

*(Lưu ý: Agent tóm tắt - Summarize Agent - thuộc về Dashboard tĩnh và không nằm trong quy mô của hệ thống điều phối hội thoại đa đặc vụ này, nó sẽ được triển khai độc lập thông qua một API sau).*

**Tech Stack:** Python, LangGraph, LangChain, FastAPI, Streamlit, Docker/Subprocess (cho sandbox), Sympy, Matplotlib.

---

### Task 1: Cấu trúc Nền Tảng Agent và State Schema ✅ Hoàn thành

Tạo cấu trúc thư mục cho hệ thống multi-agent mới và định nghĩa các module State schema sử dụng chuẩn tin nhắn của LangChain (để tương thích tuyệt đối với chức năng parallel tool calls).

**Files:**
- Tạo: `src/rag_core/state.py`
- Tạo: `src/rag_core/agents/__init__.py`
- Tạo: `src/rag_core/tools/__init__.py`

**Step 1: Viết State schema theo chuẩn MessagesState**
Định nghĩa class `State` trong `src/rag_core/state.py` mở rộng từ `MessagesState`.

```python
from langgraph.graph import MessagesState
from typing import Any, Dict

class State(MessagesState): # Cung cấp sẵn trường 'messages' chứa BaseMessage tự động reducer
    agent_output: dict = {}
    response: dict = {} # Dùng để hứng kết quả json cuối cùng render UI
    next_node: str = ""
```

**Step 2: Commit**
```bash
git add src/rag_core/state.py src/rag_core/agents/__init__.py src/rag_core/tools/__init__.py
git commit -m "feat: khởi tạo cấu trúc multi-agent và state schema chuẩn LangChain"
```

---

### Task 2: Cài Đặt Tool Code Execution Sandbox (Windows Ready) ✅ Hoàn thành

Xây dựng một tiện ích (utility) bảo mật để chạy mã Python. Vì OS server là Windows, giới hạn RAM sẽ được bỏ qua, chúng ta tập trung vào giới hạn Timeout, block code nguy hiểm bằng AST, và thu thập stdout/stderr cùng hình ảnh.

**Files:**
- Tạo: `src/rag_core/tools/sandbox.py`
- Tạo: `tests/rag_core/tools/test_sandbox.py`

**Step 1: Viết test (failing test)**
Tạo `tests/rag_core/tools/test_sandbox.py` để kiểm thử thực thi, timeout và bắt lỗi blacklist cơ bản.
```python
from src.rag_core.tools.sandbox import execute_python_code

def test_execute_python_code_success():
    result = execute_python_code("print('Hello Math')")
    assert result["success"] is True
    assert "Hello Math" in result["stdout"]

def test_execute_python_code_security():
    result = execute_python_code("import os\nos.system('echo hi')")
    assert result["success"] is False
    assert "chứa mã nguy hiểm bị cấm" in result["stderr"]
```

**Step 2: Chạy test để xác minh lỗi**
Chạy: `pytest tests/rag_core/tools/test_sandbox.py -v`
Kết quả mong đợi: LỖI (FAIL) với thông báo "ModuleNotFoundError"

**Step 3: Cài đặt code Sandbox**
Thực thi hàm `execute_python_code` trong `src/rag_core/tools/sandbox.py` sử dụng thư viện `subprocess` có cài sẵn timeout (vd: 20s). Sử dụng module `ast` để scan AST tree của code trước khi chạy, block ngay các node gọi module hệ thống (như os, sys, subprocess).

**Step 4: Chạy lại test để xác nhận Pass**
Chạy: `pytest tests/rag_core/tools/test_sandbox.py -v`
Kết quả mong đợi: PASS

**Step 5: Commit**
```bash
git add src/rag_core/tools/sandbox.py tests/rag_core/tools/test_sandbox.py
git commit -m "feat: thêm tính năng Code Execution Sandbox tool an toàn trên Windows"
```

---

### Task 3: Cài Đặt Tutor Agent ✅ Hoàn thành

Đưa logic RAG cơ sở hiện tại vào trong một mô-đun Tutor agent chuyên dụng.

**Files:**
- Tạo: `src/rag_core/agents/tutor.py`

**Step 1: Khởi tạo Tutor logic prompt và xử lý Node**
Triển khai logic gọi tool `Offline_RAG` và `hybrid search` đã có.

**Step 2: Commit**
```bash
git add src/rag_core/agents/tutor.py
git commit -m "feat: chuyển đổi base RAG logic sang mô-đun Tutor Agent"
```

---

### Task 4: Cài Đặt Sub-graph Cho Coding Agent ✅ Hoàn thành

Tạo một LangGraph sub-graph xử lý vòng lặp "Sinh Code -> Chạy Code -> Sửa lỗi (Retry)".

**Files:**
- Tạo: `src/rag_core/agents/coding.py`

**Step 1: Khai báo các workflow node**
Triển khai các hàm `generate_code`, `execute_code`, và `fix_code` trong `src/rag_core/agents/coding.py`.

**Step 2: Build the sub-graph**
Kết nối các node bằng `StateGraph` thành vòng lặp sửa lỗi (retry tối đa 3 lần).

```python
from langgraph.graph import StateGraph, START, END

def build_coding_subgraph():
    graph = StateGraph(CodingState)
    graph.add_node("generate", generate_code)
    graph.add_node("execute", execute_code)
    # ... routing logic based on success flag ...
    return graph.compile()
```

**Step 3: Commit**
```bash
git add src/rag_core/agents/coding.py
git commit -m "feat: triển khai sub-graph cho Coding Agent có vòng lặp kiểm thử code"
```

---

### Task 5: Cài Đặt Sub-graph Cho Math Agent (Sympy-First Strategy) ✅ Hoàn thành

Tạo agent chuyên dụng cho khai triển toán học. Yêu cầu agent chạy và lấy được kết quả nghiệm của Sympy MỚI sinh ra đoạn mô tả giải thích LaTeX để đảm bảo nghiệm đồng bộ, tránh đứt gãy.

**Files:**
- Tạo: `src/rag_core/agents/math.py`

**Step 1: Khai báo framework Math Node**
Triển khai hàm `verify_sympy` để tạo một mã script nháp tính nghiệm. Sau khi thu được output toán học (nếu thành công), chuỗi pipeline mới gọi `generate_derivation` sinh cấu trúc LaTeX diễn giải các bước giải thuật bám sát theo output thu được.

**Step 2: Lắp ráp toán học sub-graph**
Dựng workflow Math bằng `StateGraph`. Đảm bảo đi đúng luồng logic: Sinh code để Sympy ra kết quả -> Validate -> Soạn văn bản LaTeX.

**Step 3: Commit**
```bash
git add src/rag_core/agents/math.py
git commit -m "feat: triển khai toán học sub-graph với chiến lược Sympy First"
```

---

### Task 6: Cài Đặt Agent Tạo Quiz ✅ Hoàn thành

Triển khai Sub-Agent ép chuẩn output JSON theo mẫu để xử lý tạo câu trắc nghiệm.

**Files:**
- Tạo: `src/rag_core/agents/quiz.py`

**Step 1: Viết node Quiz Builder**
Tạo hàm `node_quiz` lợi dụng `JsonOutputParser` đảm bảo in ra định dạng câu hỏi và 4 đáp án đầy đủ kèm giải thích.

**Step 2: Commit**
```bash
git add src/rag_core/agents/quiz.py
git commit -m "feat: bổ sung Quiz Generator Agent xử lý json structured output"
```

---

### Task 7: Hợp Nhất Các Node Vào Logic Của Supervisor (Main Graph) ✅ Hoàn thành

Kết nối tất cả mọi thứ sử dụng kiến trúc Supervisor Tool-Calling (chỉ dành cho Chatspace).

**Files:**
- Thay đổi: `src/rag_core/lang_graph_rag.py`

**Step 1: Xác định lại cấu trúc Supervisor Tools**
Khai báo đồng loạt các module: `AskTutor`, `CodeAssistant`, `MathSolver`, và `GenerateQuiz` dưới dạng các tham chiếu Tool Object truyền thẳng vào LLM gốc. Thêm Supervisor node có chức năng đọc `messages` và gọi quyết định (tool call).

**Step 2: Lắp ráp Graph định tuyến**
Viết lại mã `StateGraph` cũ trên file này cho nó vai trò làm Supervisor có quyền định tuyến các luồng sang sub-graph chuyên dụng hoặc node xử lý cuối nếu gặp những trường hợp đơn giản.

```python
# Refactor `lang_graph_rag.py`
graph.add_node("supervisor", node_supervisor)
graph.add_node("tutor", node_tutor)
graph.add_node("coding", build_coding_subgraph())
# ... add edges ...
```

**Step 3: Test Local Pipeline Integration**
Thực thi command `python -m src.rag_core.lang_graph_rag` để đưa ra các bộ câu hỏi mẫu kiểm tra hệ thống điều phối graph đã vận hành chính xác.

**Step 4: Commit**
```bash
git add src/rag_core/lang_graph_rag.py
git commit -m "feat: cấu hình Supervisor Graph định tuyến đa đặc vụ theo cấu trúc MessagesState"
```

---

### Task 8: Tích Hợp Lớp Dịch Vụ API (Server Endpoint) ✅ Hoàn thành

Nâng cấp tầng FastAPI backend endpoint để tương thích với các phản hồi đa dạng của nhiều Agent.

**Files:**
- Thay đổi: `src/api/server.py` và `src/api/services/chat_service.py`

**Step 1: Đồng nhất Parser Structure**
Đảm bảo thông số từ những bộ mô-đun agents khác nhau phản hồi ra vẫn tương thích cấu trúc truyền qua cổng Schema Object `ChatResponse`. (Lưu ý: API phải map từ `messages` của LangGraph về List[dict] của App).

**Step 2: Commit**
```bash
git add src/api/services/chat_service.py
git commit -m "feat: nâng cấp endpoint chat map theo chuẩn cấu trúc mới"
```

---

## 🎉 Tổng Kết — Toàn Bộ Kế Hoạch Đã Hoàn Thành

| Task | Mô tả | Trạng thái | File |
|------|--------|------------|------|
| 1 | State Schema & Cấu trúc thư mục | ✅ | `src/rag_core/state.py` |
| 2 | Code Execution Sandbox (Windows) | ✅ | `src/rag_core/tools/sandbox.py` |
| 3 | Tutor Agent | ✅ | `src/rag_core/agents/tutor.py` |
| 4 | Coding Agent Sub-graph | ✅ | `src/rag_core/agents/coding.py` |
| 5 | Math Agent Sub-graph (Sympy-First) | ✅ | `src/rag_core/agents/math.py` |
| 6 | Quiz Agent (RAG + Trích nguồn) | ✅ | `src/rag_core/agents/quiz.py` |
| 7 | Supervisor Main Graph | ✅ | `src/rag_core/lang_graph_rag.py` |
| 8 | API Layer Integration | ✅ | `src/api/services/chat_service.py` |

**Kiến trúc luồng xử lý hoàn chỉnh:**
```
User → FastAPI → call_agent() → [Supervisor]
                                     ├── AskTutor    → Tutor Agent (RAG + Citation)
                                     ├── CodeAssistant → Coding Subgraph (Generate→Execute→Fix loop)
                                     ├── MathSolver  → Math Subgraph (Sympy→Verify→LaTeX)
                                     ├── GenerateQuiz → Quiz Agent (RAG + Citation)
                                     └── (direct)    → trả lời trực tiếp
```

**Nâng cấp sau triển khai (Quiz Agent):**
- Quiz Agent đã được nâng cấp thêm so với kế hoạch gốc: sử dụng Retrieval + Reranking để tạo câu hỏi bám sát bài giảng và đính kèm link video timestamp chính xác cho từng câu hỏi.
