import asyncio
import json
import os
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

    async def ainvoke(self, _prompt, **_kwargs):
        return _FakeResponse(self._content)


def test_generate_derivation_parses_json_and_builds_math_response(monkeypatch):
    generated_text = "Bài giải được tạo từ kết quả kiểm chứng."
    generated_data = {
        "text": generated_text,
        "goal": "Tính diện tích hình tròn",
        "steps": [
            {"title": "Công thức", "content": r"\pi r^2"},
            {"title": "Kết luận", "content": "Diện tích là $25$."},
        ],
    }
    model_output = f"```json\n{json.dumps(generated_data, ensure_ascii=False)}\n```"
    monkeypatch.setattr(math_agent, "get_llm", lambda: _FakeLLM(model_output))

    result = asyncio.run(
        math_agent.generate_derivation(
            {
                "query": "Tính diện tích hình tròn",
                "is_success": True,
                "math_result": "area = 25\nradius = 5",
            }
        )
    )

    response = result["response"]
    assert response["text"] == generated_text
    assert response["type"] == "math"
    assert response["math_data"] == {
        "goal": "Tính diện tích hình tròn",
        "steps": [
            {"title": "Công thức", "content": r"$$\pi r^2$$"},
            {"title": "Kết luận", "content": "Diện tích là $25$."},
        ],
        "verification": {
            "status": "success",
            "details": "area = 25\nradius = 5",
        },
    }
    for metadata_key in (
        "video_url",
        "title",
        "filename",
        "start_timestamp",
        "end_timestamp",
        "confidence",
    ):
        assert response[metadata_key] == []


def test_generate_derivation_uses_fallback_for_invalid_model_output(monkeypatch):
    monkeypatch.setattr(math_agent, "get_llm", lambda: _FakeLLM("not valid JSON"))
    query = "Giải phương trình x + 1 = 2"

    result = asyncio.run(
        math_agent.generate_derivation(
            {
                "query": query,
                "is_success": False,
                "math_result": "timeout",
            }
        )
    )

    response = result["response"]
    math_data = response["math_data"]
    assert response["type"] == "math"
    assert math_data["goal"] == f"Giải bài toán: {query}"
    assert query in response["text"]
    assert len(math_data["steps"]) == 3
    assert all({"title", "content"} <= set(step) for step in math_data["steps"])
    assert math_data["verification"] == {
        "status": "warning",
        "details": "timeout",
    }


def test_generate_derivation_sanitizes_undefined_verification_result(monkeypatch):
    generated_data = {
        "text": "Lời giải không phụ thuộc vào kết quả kiểm chứng.",
        "goal": "Kiểm tra biểu thức",
        "steps": [
            {"title": "Phân tích", "content": "Đối chiếu các điều kiện của bài toán."},
        ],
    }
    monkeypatch.setattr(
        math_agent,
        "get_llm",
        lambda: _FakeLLM(json.dumps(generated_data, ensure_ascii=False)),
    )

    result = asyncio.run(
        math_agent.generate_derivation(
            {
                "query": "Kiểm tra biểu thức",
                "is_success": False,
                "math_result": "undefined",
            }
        )
    )

    verification = result["response"]["math_data"]["verification"]
    assert verification["status"] == "warning"
    assert verification["details"] == "Kiểm chứng tự động chưa trả kết quả hợp lệ."
    assert "undefined" not in verification["details"].lower()
