import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

from src.rag_core.agents import math as math_agent


class _FakeResponse:
    def __init__(self, content: str):
        self.content = content


class _FakeLLM:
    def __init__(self, content: str):
        self._content = content

    def invoke(self, _prompt):
        return _FakeResponse(self._content)


class _SequenceLLM:
    def __init__(self, contents: list[str]):
        self._contents = list(contents)
        self.calls = 0

    def invoke(self, _prompt):
        if self.calls < len(self._contents):
            content = self._contents[self.calls]
        else:
            content = self._contents[-1]
        self.calls += 1
        return _FakeResponse(content)


def test_generate_derivation_success_uses_tutor_text_blocks(monkeypatch):
    monkeypatch.setattr(
        math_agent,
        "get_llm",
        lambda: _FakeLLM("Ta biến đổi biểu thức và thu được kết quả cuối cùng."),
    )

    result = math_agent.generate_derivation(
        {"query": "Tính đạo hàm của x^2", "is_success": True, "math_result": "2*x"}
    )
    response = result["response"]
    text = response["text"]

    assert "### 🎯 Mục tiêu học" in text
    assert "### 🧩 Giải theo từng bước" in text
    assert "### 🔍 Kiểm chứng kết quả" in text
    assert "### 📝 Tự luyện nhanh" in text
    assert "2*x" in text
    assert response["type"] == "math"
    assert response["video_url"] == []
    assert response["title"] == []
    assert response["filename"] == []
    assert response["start_timestamp"] == []
    assert response["end_timestamp"] == []
    assert response["confidence"] == []


def test_generate_derivation_failure_still_returns_learning_scaffold(monkeypatch):
    monkeypatch.setattr(
        math_agent,
        "get_llm",
        lambda: _FakeLLM("Hãy bắt đầu từ định nghĩa và kiểm tra lại điều kiện bài toán."),
    )

    result = math_agent.generate_derivation(
        {
            "query": "Giải phương trình log(x)=2",
            "is_success": False,
            "math_result": "Lỗi: timeout",
        }
    )
    text = result["response"]["text"]

    assert "### 🎯 Mục tiêu học" in text
    assert "### 🔍 Kiểm chứng kết quả" in text
    assert "Lỗi: timeout" in text
    assert "### 📝 Tự luyện nhanh" in text
    assert "Hãy bắt đầu từ định nghĩa" in text


def test_generate_derivation_retries_when_llm_returns_undefined(monkeypatch):
    llm = _SequenceLLM(["undefined", "Bước 1: Viết lại hàm sigmoid và đạo hàm theo quy tắc dây chuyền."])
    monkeypatch.setattr(math_agent, "get_llm", lambda: llm)

    result = math_agent.generate_derivation(
        {
            "query": "Chứng minh tính lồi/lõm của sigmoid",
            "is_success": True,
            "math_result": "sigma''(x)=sigma(x)(1-sigma(x))(1-2sigma(x))",
        }
    )
    text = result["response"]["text"].lower()

    assert "undefined" not in text
    assert "bước 1: viết lại hàm sigmoid" in text
    assert llm.calls == 2


def test_generate_derivation_normalizes_bracket_latex_to_markdown_math(monkeypatch):
    llm = _FakeLLM("Định nghĩa: [ \\sigma(x)=\\frac{1}{1+e^{-x}} ].")
    monkeypatch.setattr(math_agent, "get_llm", lambda: llm)

    result = math_agent.generate_derivation(
        {
            "query": "Tính đạo hàm sigmoid",
            "is_success": True,
            "math_result": "sigma'(x)=sigma(x)(1-sigma(x))",
        }
    )
    text = result["response"]["text"]

    assert "$$\\sigma(x)=\\frac{1}{1+e^{-x}}$$" in text
    assert "[ \\sigma(x)=\\frac{1}{1+e^{-x}} ]" not in text


def test_generate_derivation_cleans_english_noise_in_verification_block(monkeypatch):
    monkeypatch.setattr(math_agent, "get_llm", lambda: _FakeLLM("Giải theo từng bước bằng tiếng Việt."))

    result = math_agent.generate_derivation(
        {
            "query": "Tính đạo hàm sigmoid",
            "is_success": True,
            "math_result": (
                "sigma'(x) simplified = 1/(4*cosh(x/2)**2)\n"
                "Interpretation: sigma''(x) > 0 for x < 0; sigma''(x) < 0 for x > 0"
            ),
        }
    )
    text = result["response"]["text"]

    assert "Interpretation:" not in text
    assert "Diễn giải:" in text


def test_generate_derivation_repairs_fragmented_undefined_placeholder(monkeypatch):
    llm = _SequenceLLM(
        [
            "Bước 1: Viết hàm số. u n d e f i n e d",
            "Bước 1: Viết lại sigmoid, sau đó lấy đạo hàm từng bước.",
        ]
    )
    monkeypatch.setattr(math_agent, "get_llm", lambda: llm)

    result = math_agent.generate_derivation(
        {
            "query": "Chứng minh sigmoid lồi/lõm",
            "is_success": True,
            "math_result": "σ''(x)=σ(x)(1-σ(x))(1-2σ(x))",
        }
    )
    text = result["response"]["text"].lower()

    assert "u n d e f i n e d" not in text
    assert "bước 1: viết lại sigmoid" in text


def test_generate_derivation_translates_common_english_verify_phrases(monkeypatch):
    monkeypatch.setattr(math_agent, "get_llm", lambda: _FakeLLM("Giải thích ngắn gọn."))

    result = math_agent.generate_derivation(
        {
            "query": "Tính đạo hàm sigmoid",
            "is_success": True,
            "math_result": (
                "sigma'(x) in terms of sigma: sigma*(1-sigma)\n"
                "Sign of sigma''(x): Piecewise((1, x < 0), (0, Eq(x, 0)), (-1, True))"
            ),
        }
    )
    text = result["response"]["text"]

    assert "in terms of sigma" not in text
    assert "theo σ" in text
    assert "Sign of" not in text


def test_generate_derivation_formats_verification_formulas_as_latex(monkeypatch):
    monkeypatch.setattr(math_agent, "get_llm", lambda: _FakeLLM("Trình bày lời giải ngắn gọn."))

    result = math_agent.generate_derivation(
        {
            "query": "Tính đạo hàm sigmoid với sigma(x)=1/(1+e^{-x})",
            "is_success": True,
            "math_result": "sigma'(x) simplified = 1/(4*cosh(x/2)**2)",
        }
    )
    text = result["response"]["text"]

    assert "Kết quả kiểm chứng:" in text
    assert "$$σ'(x) rút gọn = 1/(4*cosh(x/2)^2)$$" in text
    assert "`" not in text


def test_generate_derivation_never_leaks_undefined_in_verification_section(monkeypatch):
    monkeypatch.setattr(math_agent, "get_llm", lambda: _FakeLLM("Giải thích theo từng bước."))

    result = math_agent.generate_derivation(
        {
            "query": "Tính đạo hàm sigmoid",
            "is_success": True,
            "math_result": "u n d e f i n e d",
        }
    )
    text = result["response"]["text"].lower()

    assert re.search(r"u\W*n\W*d\W*e\W*f\W*i\W*n\W*e\W*d", text) is None
    assert "kiểm chứng tự động chưa trả dữ liệu hợp lệ" in text
