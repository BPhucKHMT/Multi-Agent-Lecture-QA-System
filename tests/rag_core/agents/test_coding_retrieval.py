import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

from src.rag_core.agents import coding as coding_agent
from src.rag_core.agents import coding_retrieval


class _FakeResponse:
    def __init__(self, content: str):
        self.content = content


class _FakeLLM:
    def __init__(self, content: str):
        self.content = content

    async def ainvoke(self, _prompt):
        return _FakeResponse(self.content)


def test_should_use_rag_true_for_lecture_signal():
    assert coding_retrieval.should_use_rag("Giải thích theo bài giảng về linear regression") is True


def test_should_use_rag_with_course_name():
    assert coding_retrieval.should_use_rag("Tóm tắt kiến thức môn machine learning") is True


def test_should_use_rag_false_for_generic_prompt():
    assert coding_retrieval.should_use_rag("viết hàm sort mảng tăng dần") is False


def test_should_use_rag_false_for_ai_substring_in_cai_dat():
    assert coding_retrieval.should_use_rag("cai dat quicksort") is False


def test_should_use_rag_false_for_ai_substring_in_giai_thuat():
    assert coding_retrieval.should_use_rag("giai thuat sap xep") is False


def test_retrieve_lecture_context_returns_empty_on_no_docs(monkeypatch):
    class _FakeRetriever:
        def invoke(self, _query):
            return []

    monkeypatch.setattr(coding_retrieval.resource_manager, "get_hybrid_retriever", lambda: _FakeRetriever())
    monkeypatch.setattr(coding_retrieval.resource_manager, "get_tutor_reranker", lambda: object())

    assert coding_retrieval.retrieve_lecture_context("query không khớp") == ("", [])


def test_retrieve_lecture_context_returns_empty_on_exception(monkeypatch):
    def _raise_error():
        raise RuntimeError("retriever unavailable")

    monkeypatch.setattr(coding_retrieval.resource_manager, "get_hybrid_retriever", _raise_error)

    assert coding_retrieval.retrieve_lecture_context("query bất kỳ") == ("", [])


def test_generate_code_propagates_lecture_citations(monkeypatch):
    llm = _FakeLLM("```python\nprint('ok')\n```")
    references = [{
        "video_url": "https://video.example/lecture",
        "title": "Linear regression",
        "filename": "lecture.mp4",
        "start_timestamp": "00:01",
        "end_timestamp": "00:03",
    }]
    monkeypatch.setattr(coding_agent, "get_llm", lambda: llm)
    monkeypatch.setattr(coding_retrieval, "should_use_rag", lambda _query: True)
    monkeypatch.setattr(
        coding_retrieval,
        "retrieve_lecture_context",
        lambda _query, top_k=3: ("Nội dung bài giảng", references),
    )

    result = asyncio.run(
        coding_agent.generate_code({"query": "Viết code linear regression", "retry_count": 0})
    )

    assert result["code"] == "print('ok')"
    assert result["references"] == references


def test_generate_code_returns_no_citations_without_lecture_context(monkeypatch):
    llm = _FakeLLM("```python\nprint('ok')\n```")
    references = [{
        "video_url": "https://video.example/lecture",
        "title": "Should not be used",
    }]
    monkeypatch.setattr(coding_agent, "get_llm", lambda: llm)
    monkeypatch.setattr(coding_retrieval, "should_use_rag", lambda _query: False)
    monkeypatch.setattr(
        coding_retrieval,
        "retrieve_lecture_context",
        lambda _query, top_k=3: ("sẽ không dùng", references),
    )

    result = asyncio.run(
        coding_agent.generate_code({"query": "Viết hàm cộng hai số", "retry_count": 0})
    )

    assert result["code"] == "print('ok')"
    assert result["references"] == []
