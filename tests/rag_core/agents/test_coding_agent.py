import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

from src.rag_core.agents import coding as coding_agent


class _FakeResponse:
    def __init__(self, content: str):
        self.content = content


class _FakeLLM:
    def __init__(self, content: str):
        self._content = content

    def invoke(self, _prompt):
        return _FakeResponse(self._content)


class _SequenceLLM:
    def __init__(self, contents):
        self._contents = list(contents)

    def invoke(self, _prompt):
        if not self._contents:
            raise AssertionError("LLM bị gọi nhiều hơn số response đã cấu hình")
        return _FakeResponse(self._contents.pop(0))


def test_extract_code_handles_capitalized_python_fence():
    text = "```Python\nprint('Hello')\n```"
    assert coding_agent.extract_code(text) == "print('Hello')"


def test_extract_code_handles_crlf_fences():
    text = "```python\r\nprint('CRLF')\r\n```"
    assert coding_agent.extract_code(text) == "print('CRLF')"


def test_extract_code_handles_no_newline_before_closing_fence():
    text = "```python\nprint('No newline')```"
    assert coding_agent.extract_code(text) == "print('No newline')"


def test_extract_code_falls_back_to_first_fenced_block():
    text = "Trả lời:\n```javascript\nconsole.log('x')\n```"
    assert coding_agent.extract_code(text) == "console.log('x')"


# ---------------------------------------------------------------------------
# Test: heavy code (DL training) → không execute, trả hướng dẫn local
# ---------------------------------------------------------------------------

def test_coding_agent_heavy_tensorflow_skips_sandbox(monkeypatch):
    """Code TensorFlow training không được execute — response có hướng dẫn chạy local."""
    tf_code = (
        "```python\n"
        "import tensorflow as tf\n"
        "model = tf.keras.Sequential([tf.keras.layers.Dense(1)])\n"
        "model.compile(optimizer='adam', loss='mse')\n"
        "model.fit(x_train, y_train, epochs=50)\n"
        "```"
    )
    monkeypatch.setattr(coding_agent, "get_llm", lambda: _FakeLLM(tf_code))

    # Đảm bảo sandbox không được gọi
    sandbox_called = {"called": False}
    def _fake_execute(code, **_):
        sandbox_called["called"] = True
        return {"success": True, "stdout": "", "stderr": ""}
    monkeypatch.setattr(coding_agent, "execute_python_code", _fake_execute)

    graph = coding_agent.build_coding_subgraph()
    result = graph.invoke({"query": "Viết code train linear model bằng TensorFlow"})

    assert sandbox_called["called"] is False, "Sandbox không được gọi với heavy code"
    text = result["response"]["text"]
    assert "chạy ở local" in text
    assert "solution.py" in text
    assert result["response"]["type"] == "coding"


def test_coding_agent_simple_code_executes_normally(monkeypatch):
    """Code đơn giản vẫn chạy bình thường qua sandbox."""
    simple_code = "```python\nprint('Hello World')\n```"
    monkeypatch.setattr(coding_agent, "get_llm", lambda: _FakeLLM(simple_code))

    sandbox_called = {"called": False}
    def _fake_execute(code, **_):
        sandbox_called["called"] = True
        return {"success": True, "stdout": "Hello World\n", "stderr": ""}
    monkeypatch.setattr(coding_agent, "execute_python_code", _fake_execute)

    graph = coding_agent.build_coding_subgraph()
    result = graph.invoke({"query": "In ra Hello World"})

    assert sandbox_called["called"] is True, "Sandbox phải được gọi với code đơn giản"
    text = result["response"]["text"]
    assert "Hello World" in text
    assert "chạy ở local" not in text


def test_coding_agent_retry_reclassifies_heavy_code_before_execute(monkeypatch):
    """Sau fix_code, graph phải classify lại để chặn heavy code trước khi execute."""
    initial_code = "```python\nprint(1/0)\n```"
    heavy_fixed_code = (
        "```python\n"
        "import tensorflow as tf\n"
        "model = tf.keras.Sequential([tf.keras.layers.Dense(1)])\n"
        "model.compile(optimizer='adam', loss='mse')\n"
        "model.fit(x_train, y_train, epochs=10)\n"
        "```"
    )
    explanation = "Đoạn model.fit sẽ lặp nhiều epoch nên cần chạy local."
    llm = _SequenceLLM([initial_code, heavy_fixed_code, explanation])
    monkeypatch.setattr(coding_agent, "get_llm", lambda: llm)

    executed_codes = []

    def _fake_execute(code, **_):
        executed_codes.append(code)
        if len(executed_codes) == 1:
            return {"success": False, "stdout": "", "stderr": "ZeroDivisionError"}
        return {"success": True, "stdout": "unexpected heavy run", "stderr": ""}

    monkeypatch.setattr(coding_agent, "execute_python_code", _fake_execute)

    graph = coding_agent.build_coding_subgraph()
    result = graph.invoke({"query": "Viết code train model TensorFlow"})

    text = result["response"]["text"]
    assert "chạy ở local" in text
    assert "solution.py" in text
    assert len(executed_codes) == 1
    assert result["response"]["type"] == "coding"


def test_coding_agent_heavy_response_has_code_block(monkeypatch):
    """Response của heavy code phải chứa code block đầy đủ để người học copy."""
    torch_code = (
        "```python\n"
        "import torch\n"
        "for epoch in range(100):\n"
        "    loss = compute_loss()\n"
        "    optimizer.step()\n"
        "```"
    )
    monkeypatch.setattr(coding_agent, "get_llm", lambda: _FakeLLM(torch_code))

    graph = coding_agent.build_coding_subgraph()
    result = graph.invoke({"query": "Viết training loop PyTorch"})

    text = result["response"]["text"]
    assert "```python" in text
    assert "for epoch in range(100):" in text


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
    assert "Dòng model.compile thiết lập hàm mất mát MSE và bộ tối ưu Adam." in text
    assert "chạy ở local" in text
