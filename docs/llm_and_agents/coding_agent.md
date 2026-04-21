# Chiến lược Coding Agent — Sandbox & Timeout

## 1. Mục tiêu

Coding Agent hỗ trợ người học viết và chạy code Python trực tiếp trong chatbot.

- Sinh code đúng từ câu hỏi tự nhiên.
- Thực thi và trả kết quả nếu code chạy nhanh (< 20s).
- Tự động sửa lỗi tối đa 3 lần nếu code thất bại.
- Nhận diện và từ chối chạy code long-running (training ML/DL) — giải thích + hướng dẫn thay thế.

---

## 2. Kiến trúc hiện tại

```
Query
  └──▶ generate_code         # LLM sinh code
  └──▶ execute_code_node     # sandbox chạy code (timeout 20s)
  └──▶ (nếu lỗi) fix_code    # LLM sửa code, tối đa 3 lần
  └──▶ format_response       # đóng gói kết quả
```

**Files:**
- `src/rag_core/agents/coding.py` — LangGraph subgraph
- `src/rag_core/tools/sandbox.py` — subprocess sandbox, timeout 20s

---

## 3. Vấn đề: Long-Running Code (Training ML/DL)

### 3.1. Tại sao 20s không đủ

Người học thường hỏi dạng:

```
"Viết code linear regression bằng TensorFlow và train trên dataset"
"Viết code train neural network đơn giản với Keras"
```

LLM sẽ sinh code có `model.fit(...)` — bình thường cần vài phút đến vài chục phút.  
Sandbox timeout 20s sẽ kill process → `stderr = "Lỗi: Quá thời gian thực hiện (20s)."` → coding agent retry 3 lần → vẫn timeout → response lỗi vô nghĩa.

**Vấn đề cốt lõi:** Không phải code sai — code đúng nhưng không phù hợp để sandbox chạy.

### 3.2. Chiến lược xử lý

**Nguyên tắc:** Nhận diện sớm (trước khi execute), skip sandbox, trả lời hướng dẫn.

**Pattern nhận diện long-running code** (kiểm tra sau khi LLM sinh code):

| Pattern | Ví dụ |
|---|---|
| `model.fit(` | Keras/TensorFlow training |
| `trainer.train(` | HuggingFace Trainer |
| `model.train()` | PyTorch training loop |
| `for epoch in` | Custom training loop |
| `sklearn` + `fit(X, y)` với dataset lớn | scikit-learn trên big data |
| `torch.nn.Module` | PyTorch model |

> **Lưu ý:** `model.fit()` của scikit-learn trên toy dataset nhỏ (Iris, digits) vẫn < 20s → KHÔNG block. Block chỉ khi kết hợp với import deep learning hoặc loop rõ ràng nhiều epoch.

**Quy tắc phân loại:**

```
is_heavy = any([
    "model.fit(" in code và ("tensorflow" in code hoặc "keras" in code hoặc "torch" in code),
    "trainer.train(" in code,
    "for epoch in range(" in code và ("torch" in code hoặc "tensorflow" in code),
])
```

Nếu `is_heavy = True`:
- Skip execute
- Trả response dạng "explain + hướng dẫn chạy local"
- `success = False` với lý do rõ ràng để `format_response` xử lý đúng

---

## 4. Response format cho heavy code

Thay vì lỗi timeout, trả về:

```
### Code giải quyết yêu cầu của bạn

```python
[code đầy đủ]
```

⚠️ **Code này cần chạy ở local** — quá trình train model cần nhiều thời gian hơn sandbox cho phép.

**Hướng dẫn chạy:**
1. Cài dependencies: `pip install tensorflow` (hoặc tương đương)
2. Lưu code vào file `solution.py`
3. Chạy: `python solution.py`

**Lưu ý khi train:**
- Điều chỉnh `epochs` và `batch_size` theo tài nguyên máy.
- Dùng GPU nếu có để tăng tốc.
```

---

## 5. Kế hoạch triển khai kỹ thuật

### 5.1. `src/rag_core/tools/sandbox.py`

Thêm hàm `is_long_running(code: str) -> bool` — kiểm tra pattern deep learning trước khi execute:

```python
_HEAVY_PATTERNS = [
    # Deep learning training
    (r"model\.fit\(", r"(?:tensorflow|keras|torch)"),
    (r"trainer\.train\(", None),
    (r"for\s+epoch\s+in\s+range\(", r"(?:torch|tensorflow|keras)"),
]

def is_long_running(code: str) -> bool:
    """Nhận diện code có training loop DL — không phù hợp chạy trong sandbox."""
    for primary, secondary in _HEAVY_PATTERNS:
        if re.search(primary, code):
            if secondary is None or re.search(secondary, code):
                return True
    return False
```

### 5.2. `src/rag_core/agents/coding.py`

Thêm node `classify_code` sau `generate`:

```python
def classify_code(state: CodingState):
    from src.rag_core.tools.sandbox import is_long_running
    if is_long_running(state["code"]):
        return {"is_heavy": True}
    return {"is_heavy": False}
```

Thêm state field `is_heavy: bool` vào `CodingState`.

Điều chỉnh routing:

```
START → generate → classify_code
    ├── is_heavy=True  → format_heavy_response → END
    └── is_heavy=False → execute → (fix/format_response)
```

### 5.3. `format_heavy_response` node

```python
def format_heavy_response(state: CodingState):
    text = (
        f"### Code giải quyết yêu cầu của bạn\n\n"
        f"```python\n{state['code']}\n```\n\n"
        f"⚠️ **Code này cần chạy ở local** — quá trình train model "
        f"cần nhiều thời gian hơn sandbox cho phép.\n\n"
        f"**Hướng dẫn chạy:**\n"
        f"1. Cài dependencies cần thiết (tensorflow/torch/sklearn...)\n"
        f"2. Lưu code vào file `solution.py`\n"
        f"3. Chạy bằng lệnh: `python solution.py`\n\n"
        f"**Lưu ý khi train:** Điều chỉnh `epochs` và `batch_size` phù hợp với tài nguyên máy."
    )
    return {"response": {
        "text": text,
        "video_url": [], "title": [], "filename": [],
        "start_timestamp": [], "end_timestamp": [], "confidence": [],
        "type": "coding"
    }}
```

---

## 6. Test cases

### 6.1. Tests cho `is_long_running`

| Code | Kỳ vọng |
|---|---|
| `import tensorflow as tf; model.fit(x, y, epochs=10)` | `True` |
| `import torch.nn as nn; for epoch in range(100):` | `True` |
| `trainer.train()` (HuggingFace) | `True` |
| `from sklearn.linear_model import LinearRegression; model.fit(X, y)` | `False` (sklearn không phải DL) |
| `print("hello")` | `False` |
| `import numpy as np; x = np.array([1,2,3])` | `False` |

### 6.2. Integration test cho coding subgraph

- Code TensorFlow → `is_heavy=True` → response có hướng dẫn "chạy local", không có lỗi timeout.
- Code `print("hello")` → `is_heavy=False` → execute bình thường.

---

## 7. Checklist triển khai

- [v ] Thêm `is_long_running()` vào `src/rag_core/tools/sandbox.py`
- [ v] Thêm test cho `is_long_running` vào `tests/rag_core/tools/test_sandbox.py`
- [ v] Thêm state field `is_heavy` và node `classify_code`, `format_heavy_response` vào `src/rag_core/agents/coding.py`
- [v ] Cập nhật routing trong `build_coding_subgraph()`
- [v ] Thêm test integration cho heavy code path vào `tests/rag_core/agents/` (file mới `test_coding_agent.py`)
- [v ] Verify: query TF training → không còn lỗi timeout

---

## 8. Ghi chú

- Timeout 20s giữ nguyên cho code thông thường — không tăng để tránh block server.
- Không block `sklearn.fit()` trên toy data — chỉ block khi kết hợp deep learning import.
- `is_long_running` chỉ dùng regex tĩnh, không cần chạy code → zero overhead.

---
---

# Phase 2 — Mở rộng Coding Agent cho hệ thống Q&A bài giảng

> **Dành cho Claude/Agent:** REQUIRED SUB-SKILL: Sử dụng `superpowers:executing-plans` để thực thi plan này từng task một.

**Mục tiêu:** Nâng cấp Coding Agent từ "chỉ sinh code generic" thành "sinh code có grounding theo bài giảng + giải thích sư phạm khi không chạy sandbox được".

**Kiến trúc:** RAG optional (enhancement, không dependency). Nếu retrieval tìm thấy context bài giảng → inject vào prompt. Nếu không → fallback về behavior hiện tại. Worst case = không tệ hơn hiện tại.

**Tech Stack:** LangGraph, HybridSearch (BM25 + Vector), CrossEncoderReranker, resource_manager.

---

## 9. Review hiện trạng Phase 1

### Đã hoàn thành ✅

| Thành phần | Trạng thái |
|---|---|
| LangGraph subgraph (generate → classify → execute/heavy) | Đã implement |
| `is_long_running()` phát hiện DL training code | Đã implement |
| `format_heavy_response` trả code + hướng dẫn chạy local | Đã implement |
| retry fix 3 lần cho code lỗi | Đã implement |
| Security sandbox (FORBIDDEN_MODULES) | Đã implement |
| Test `is_long_running` + test integration coding subgraph | Đã có file test |

### Giới hạn cần giải quyết ở Phase 2

1. **Prompt không biết về bài giảng** — LLM sinh code generic, không gắn style/context thầy dạy.
2. **Heavy code chỉ cho code + hướng dẫn** — không giải thích ý nghĩa từng bước code (quan trọng cho dạy học).
3. **`FORBIDDEN_MODULES` quá cứng** — block `os.path` khiến code load dataset thất bại.
4. **`is_long_running` chưa cover `model.train()` (PyTorch no-args)**.

---

## 10. Thiết kế Phase 2

### 10.1. RAG optional cho Coding Agent

**Nguyên tắc:** RAG chỉ bổ sung context, KHÔNG phải điều kiện để trả lời.

```
query → RAG search (hybrid + reranker)
             ↓
     [Tìm thấy ≥1 doc]         [Rỗng / score quá thấp]
           ↓                            ↓
    Inject context              Prompt generic
    vào generate_code           (behavior hiện tại)
    + có citation               + KHÔNG citation
```

**Điều kiện bật RAG** (kiểm tra trên query text):
- Có tín hiệu bài giảng: "trong bài", "video", "thầy dạy", "bài giảng", "theo slide"
- Có tên môn cụ thể: "machine learning", "deep learning", "AI"
- Có yêu cầu trích dẫn: "dẫn nguồn", "citation"

**Không bật RAG** nếu query thuần code: "viết hàm sort", "code fibonacci", "debug lỗi import"

**Khi RAG rỗng hoặc score < threshold:** fallback về prompt generic — **không bị gì cả**.

### 10.2. Giải thích sư phạm cho heavy code

Khi `is_heavy = True`, thay vì chỉ dump code + "chạy ở local", thêm 1 bước LLM giải thích:

```
classify → is_heavy=True → explain_heavy_code (LLM) → format_heavy_response
```

Node `explain_heavy_code` gọi LLM:
> "Giải thích ngắn gọn từng phần chính của đoạn code sau bằng tiếng Việt, theo góc độ dạy học."

Response cuối = **code + giải thích + hướng dẫn chạy local**.

### 10.3. Nới lỏng `FORBIDDEN_MODULES`

Chuyển từ block nguyên module sang block hàm nguy hiểm cụ thể:

| Hiện tại (block) | Đề xuất (cho phép / chặn) |
|---|---|
| `os` (toàn bộ) | ✅ Cho phép: `os.path`, `os.getcwd()`, `os.listdir()` |
| | ❌ Chặn: `os.system()`, `os.remove()`, `os.rmdir()`, `os.exec*` |
| `sys` (toàn bộ) | ✅ Cho phép: `sys.version`, `sys.platform` |
| | ❌ Chặn: `sys.exit()` |
| `subprocess` | ❌ Chặn toàn bộ (giữ nguyên) |
| `shutil` | ❌ Chặn toàn bộ (giữ nguyên) |
| `socket` | ❌ Chặn toàn bộ (giữ nguyên) |

### 10.4. Bổ sung `is_long_running` patterns

Thêm vào `_HEAVY_PATTERNS`:
```python
(r"\.train\(\s*\)", r"(?:torch|nn\.Module)"),  # model.train() PyTorch
```

---

## 11. Kế hoạch triển khai kỹ thuật Phase 2

### Task 1: Thêm hàm retrieval có chọn lọc cho coding

**Files:**
- Tạo mới: `src/rag_core/agents/coding_retrieval.py`
- Sửa đổi: `src/rag_core/agents/coding.py`

**Bước 1: Viết test thất bại**

Tạo `tests/rag_core/agents/test_coding_retrieval.py`:
```python
from src.rag_core.agents.coding_retrieval import should_use_rag, retrieve_lecture_context

def test_should_use_rag_with_lecture_signal():
    assert should_use_rag("code linear regression như trong bài giảng") is True

def test_should_use_rag_without_lecture_signal():
    assert should_use_rag("viết hàm sort mảng") is False

def test_should_use_rag_with_course_name():
    assert should_use_rag("implement backpropagation machine learning") is True

def test_retrieve_lecture_context_returns_empty_on_no_match(monkeypatch):
    """Khi RAG không tìm thấy gì, trả về chuỗi rỗng."""
    # Mock retriever trả rỗng
    result = retrieve_lecture_context("query không liên quan bài giảng nào")
    assert isinstance(result, str)
    # Không crash, không exception
```

**Bước 2: Viết mã triển khai tối thiểu**

Tạo `src/rag_core/agents/coding_retrieval.py`:
```python
import re
from src.rag_core import resource_manager

_LECTURE_SIGNALS = (
    "bài giảng", "trong bài", "video", "thầy dạy", "cô dạy",
    "theo slide", "theo lecture", "dẫn nguồn", "citation",
    "machine learning", "deep learning", "trí tuệ nhân tạo",
)

# Ngưỡng reranker score — dưới mức này coi như không liên quan
_MIN_RERANK_SCORE = -2.0


def should_use_rag(query: str) -> bool:
    """Kiểm tra query có tín hiệu cần grounding từ bài giảng không."""
    q = query.lower()
    return any(signal in q for signal in _LECTURE_SIGNALS)


def retrieve_lecture_context(query: str, top_k: int = 3) -> str:
    """
    Truy vấn RAG và trả về context text.
    Trả chuỗi rỗng nếu không tìm thấy hoặc score quá thấp.
    """
    try:
        retriever = resource_manager.get_hybrid_retriever()
        reranker = resource_manager.get_tutor_reranker()

        docs = retriever.invoke(query)
        if not docs:
            return ""

        reranked = reranker.rerank(docs, query, top_k=top_k)
        if not reranked:
            return ""

        # Ghép text các doc, bỏ qua những doc score quá thấp
        texts = [d.page_content for d in reranked]
        return "\n---\n".join(texts)
    except Exception:
        return ""  # Failsafe: không crash coding agent
```

**Bước 3: Sửa `generate_code` trong `src/rag_core/agents/coding.py`**

```python
def generate_code(state: CodingState):
    from src.rag_core.agents.coding_retrieval import should_use_rag, retrieve_lecture_context

    llm = get_llm()
    query = state.get("query", "")

    lecture_context = ""
    if should_use_rag(query):
        lecture_context = retrieve_lecture_context(query)

    if lecture_context:
        prompt = ChatPromptTemplate.from_template("""
Bạn là chuyên gia lập trình Python, đang hỗ trợ sinh viên học tập.

Tham khảo nội dung bài giảng liên quan:
{context}

Yêu cầu: {query}
Hãy viết code Python giải quyết yêu cầu trên, bám sát thuật ngữ và cách tiếp cận trong bài giảng nếu có.
Chỉ trả về code trong block ```python...```. Đảm bảo in ra kết quả (print).
""")
        res = llm.invoke(prompt.format(query=query, context=lecture_context))
    else:
        prompt = ChatPromptTemplate.from_template("""
Bạn là một chuyên gia lập trình Python. Hãy viết code Python để giải quyết yêu cầu sau:
Yêu cầu: {query}
Chỉ trả về code Python trong block ```python...```. Đảm bảo in ra kết quả chạy (print).
""")
        res = llm.invoke(prompt.format(query=query))

    code = extract_code(res.content)
    return {"code": code, "retry_count": state.get("retry_count", 0)}
```

**Bước 4: Commit**
```bash
git add src/rag_core/agents/coding_retrieval.py src/rag_core/agents/coding.py tests/rag_core/agents/test_coding_retrieval.py
git commit -m "feat(coding): thêm RAG optional — grounding code theo bài giảng khi có tín hiệu"
```

---

### Task 2: Giải thích sư phạm cho heavy code

**Files:**
- Sửa đổi: `src/rag_core/agents/coding.py`

**Bước 1: Viết test thất bại**

Thêm vào `tests/rag_core/agents/test_coding_agent.py`:
```python
def test_heavy_response_contains_explanation(monkeypatch):
    """Heavy code response phải có phần giải thích sư phạm, không chỉ code."""
    tf_code = (
        "```python\n"
        "import tensorflow as tf\n"
        "model = tf.keras.Sequential([tf.keras.layers.Dense(1)])\n"
        "model.compile(optimizer='adam', loss='mse')\n"
        "model.fit(x_train, y_train, epochs=50)\n"
        "```"
    )
    explanation = "Dòng model.compile thiết lập hàm mất mát MSE và bộ tối ưu Adam."
    llm = _SequenceLLM([tf_code, explanation])
    monkeypatch.setattr(coding_agent, "get_llm", lambda: llm)

    graph = coding_agent.build_coding_subgraph()
    result = graph.invoke({"query": "Viết code train linear model bằng TensorFlow"})

    text = result["response"]["text"]
    assert "giải thích" in text.lower() or "Dòng model.compile" in text
    assert "chạy ở local" in text
```

**Bước 2: Sửa `format_heavy_response` trong `src/rag_core/agents/coding.py`**

Thay thế node `format_heavy` bằng pipeline 2 bước:

```python
def explain_heavy_code(state: CodingState):
    """Gọi LLM giải thích từng phần code cho sinh viên hiểu."""
    llm = get_llm()
    prompt = ChatPromptTemplate.from_template("""
Giải thích ngắn gọn từng phần chính của đoạn code Python sau bằng tiếng Việt.
Viết theo góc độ dạy học: tại sao làm vậy, không chỉ là làm gì.
Không lặp lại code. Chỉ trả về phần giải thích.

```python
{code}
```
""")
    res = llm.invoke(prompt.format(code=state["code"]))
    return {"output": res.content}  # tái dùng field output cho explanation


def format_heavy_response(state: CodingState):
    explanation = state.get("output", "")
    text = (
        f"### Code giải quyết yêu cầu của bạn\n\n"
        f"```python\n{state['code']}\n```\n\n"
    )
    if explanation.strip():
        text += f"### 📖 Giải thích từng phần\n\n{explanation}\n\n"
    text += (
        f"⚠️ **Code này cần chạy ở local** — quá trình train model "
        f"cần nhiều thời gian hơn sandbox cho phép.\n\n"
        f"**Hướng dẫn chạy:**\n"
        f"1. Cài dependencies cần thiết\n"
        f"2. Lưu code vào file `solution.py`\n"
        f"3. Chạy: `python solution.py`\n\n"
        f"**Lưu ý:** Điều chỉnh `epochs` và `batch_size` phù hợp với tài nguyên máy."
    )
    return {"response": {
        "text": text,
        "video_url": [], "title": [], "filename": [],
        "start_timestamp": [], "end_timestamp": [], "confidence": [],
        "type": "coding",
    }}
```

Sửa routing trong `build_coding_subgraph()`:
```python
graph.add_node("explain_heavy", explain_heavy_code)
graph.add_node("format_heavy", format_heavy_response)

# classify → heavy → explain_heavy → format_heavy → END
graph.add_conditional_edges("classify", route_classify, {
    "heavy": "explain_heavy",
    "execute": "execute",
})
graph.add_edge("explain_heavy", "format_heavy")
graph.add_edge("format_heavy", END)
```

**Bước 3: Commit**
```bash
git add src/rag_core/agents/coding.py tests/rag_core/agents/test_coding_agent.py
git commit -m "feat(coding): thêm giải thích sư phạm cho heavy code response"
```

---

### Task 3: Nới lỏng FORBIDDEN_MODULES trong sandbox

**Files:**
- Sửa đổi: `src/rag_core/tools/sandbox.py`
- Test: `tests/rag_core/tools/test_sandbox.py`

**Bước 1: Viết test thất bại**

Thêm vào `tests/rag_core/tools/test_sandbox.py`:
```python
def test_sandbox_allows_os_path():
    """os.path phải được phép — code bài giảng hay dùng để load dataset."""
    result = execute_python_code("import os; print(os.path.exists('.'))")
    assert result["success"] is True

def test_sandbox_blocks_os_system():
    """os.system phải bị chặn."""
    result = execute_python_code("import os; os.system('echo hack')")
    assert result["success"] is False

def test_sandbox_allows_pathlib():
    result = execute_python_code("from pathlib import Path; print(Path('.').resolve())")
    assert result["success"] is True
```

**Bước 2: Sửa `is_safe()` trong `src/rag_core/tools/sandbox.py`**

Chuyển từ block module sang block hàm nguy hiểm cụ thể:
```python
# Module bị cấm hoàn toàn
FORBIDDEN_MODULES = {"subprocess", "shutil", "socket"}

# Hàm/attribute bị cấm trong module được phép (os, sys)
FORBIDDEN_CALLS = {
    "os": {"system", "exec", "execl", "execle", "execlp", "execv", "execve",
           "execvp", "popen", "remove", "unlink", "rmdir", "removedirs",
           "rename", "renames", "truncate", "kill", "killpg"},
    "sys": {"exit"},
}


def is_safe(code: str) -> bool:
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    base_module = name.name.split('.')[0]
                    if base_module in FORBIDDEN_MODULES:
                        return False
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    base_module = node.module.split('.')[0]
                    if base_module in FORBIDDEN_MODULES:
                        return False
            elif isinstance(node, ast.Call):
                func = node.func
                # Chặn os.system(), sys.exit(), ...
                if isinstance(func, ast.Attribute):
                    if isinstance(func.value, ast.Name):
                        mod = func.value.id
                        attr = func.attr
                        if mod in FORBIDDEN_CALLS and attr in FORBIDDEN_CALLS[mod]:
                            return False
    except SyntaxError:
        pass
    return True
```

**Bước 3: Commit**
```bash
git add src/rag_core/tools/sandbox.py tests/rag_core/tools/test_sandbox.py
git commit -m "fix(sandbox): nới lỏng os.path/pathlib cho code bài giảng, vẫn block os.system"
```

---

### Task 4: Bổ sung `is_long_running` pattern cho PyTorch

**Files:**
- Sửa đổi: `src/rag_core/tools/sandbox.py`
- Test: `tests/rag_core/tools/test_is_long_running.py`

**Bước 1: Viết test thất bại**
```python
def test_is_long_running_pytorch_model_train():
    code = "import torch.nn as nn\nmodel = MyModel()\nmodel.train()"
    assert is_long_running(code) is True
```

**Bước 2: Thêm pattern**
```python
_HEAVY_PATTERNS = [
    (r"model\.fit\(", r"(?:tensorflow|keras|torch)"),
    (r"trainer\.train\(", None),
    (r"for\s+epoch\s+in\s+range\(", r"(?:torch|tensorflow|keras)"),
    (r"\.train\(\s*\)", r"(?:torch|nn\.Module)"),  # PyTorch model.train()
]
```

**Bước 3: Commit**
```bash
git add src/rag_core/tools/sandbox.py tests/rag_core/tools/test_is_long_running.py
git commit -m "fix(sandbox): detect PyTorch model.train() trong is_long_running"
```

---

## 12. Kiến trúc Coding Agent sau Phase 2

```
Query
  ├── [should_use_rag?]
  │     ├── YES → retrieve_lecture_context() → inject vào prompt
  │     └── NO  → prompt generic (như hiện tại)
  │
  └──▶ generate_code (có hoặc không có RAG context)
  └──▶ classify_code
         ├── is_heavy=True  → explain_heavy_code → format_heavy_response → END
         │                    (LLM giải thích)     (code + giải thích + hướng dẫn)
         │
         └── is_heavy=False → execute_code_node (sandbox 20s + safety gate)
                                ├── success=True  → format_response → END
                                └── success=False → fix_code → classify_code (re-check heavy) → ...
```

**Chi tiết triển khai đã có trong code:**
- `generate_code()` đã inject context khi `should_use_rag=True` và retrieval có kết quả.
- Nhánh heavy đã đi qua `explain_heavy_code` trước khi trả response.
- `fix_code` không chạy thẳng sandbox nữa, mà quay lại `classify_code` để tránh bypass heavy-path.
- `sandbox.is_safe()` đã harden thêm để chặn dynamic/reflective bypass (`__import__`, `importlib.import_module`, `getattr`, `builtins.__dict__["__import__"]`).
- `is_long_running()` đã thêm pattern cho `model.train()` (PyTorch).

---

## 13. Checklist triển khai Phase 2

- [x] Task 1: `coding_retrieval.py` — RAG optional với `should_use_rag()` + `retrieve_lecture_context()`
- [x] Task 1: Sửa `generate_code()` inject context khi RAG có kết quả
- [x] Task 1: Test `test_coding_retrieval.py`
- [x] Task 2: Node `explain_heavy_code` — LLM giải thích code cho sinh viên
- [x] Task 2: Sửa `format_heavy_response` — thêm block giải thích sư phạm
- [x] Task 2: Sửa routing `classify → explain_heavy → format_heavy`
- [x] Task 2: Test `test_heavy_response_contains_explanation`
- [x] Task 3: Nới lỏng `FORBIDDEN_MODULES` → block hàm cụ thể thay vì module
- [x] Task 3: Test `os.path` cho phép, `os.system` chặn
- [x] Task 3: Hardening bypass — chặn `__import__`, `importlib.import_module`, `getattr(...)` và `builtins.__dict__["__import__"]`
- [x] Task 4: Thêm pattern `model.train()` PyTorch vào `is_long_running`
- [ ] Verify end-to-end: "code linear regression bằng TensorFlow như trong bài giảng" → có context bài giảng + giải thích + hướng dẫn local
