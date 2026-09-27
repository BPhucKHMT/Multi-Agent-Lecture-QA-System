import json
import os
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

from prometheus_client import REGISTRY
from src.rag_core.offline_rag import Offline_RAG


class _FakeDoc:
    def __init__(self, content: str):
        self.page_content = content
        self.metadata = {
            "video_url": "https://youtube.com/watch?v=abc",
            "filename": "file.txt",
            "title": "title",
            "start_timestamp": "00:00:01",
            "end_timestamp": "00:00:05",
        }





@pytest.mark.anyio
async def test_get_context_deduplicates_docs_and_preserves_citation_metadata(monkeypatch):
    class Retriever:
        async def ainvoke(self, _query):
            return [_FakeDoc("first"), _FakeDoc("first"), _FakeDoc("second")]

    class Reranker:
        def rerank(self, docs, _query):
            return docs

    rag = Offline_RAG(llm=object(), retriever=Retriever(), reranker=Reranker())

    async def queries(query, _history):
        return [query, "related query"]

    monkeypatch.setattr(rag, "generate_queries", queries)
    payload = json.loads(await rag.get_context("CNN là gì?"))

    assert [item["content"] for item in payload] == ["first", "second"]
    assert [item["filename"] for item in payload] == ["file.txt", "file.txt"]
    assert [item["start_timestamp"] for item in payload] == ["00:00:01", "00:00:01"]




@pytest.mark.anyio
async def test_reranker_failure_is_counted_without_changing_exception(monkeypatch):
    class Retriever:
        async def ainvoke(self, _query):
            return [_FakeDoc("CNN context")]

    class FailingReranker:
        def rerank(self, _docs, _query):
            raise RuntimeError("reranker unavailable")

    rag = Offline_RAG(
        llm=object(), retriever=Retriever(), reranker=FailingReranker()
    )

    async def queries(query, _history):
        return [query]

    monkeypatch.setattr(rag, "generate_queries", queries)
    labels = {"stage": "rerank", "outcome": "error"}
    before = REGISTRY.get_sample_value("puq_rag_stage_duration_seconds_count", labels) or 0

    with pytest.raises(RuntimeError, match="reranker unavailable"):
        await rag.get_context("CNN là gì?")

    assert (REGISTRY.get_sample_value("puq_rag_stage_duration_seconds_count", labels) or 0) == before + 1
