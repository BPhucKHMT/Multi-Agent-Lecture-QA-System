import json
import os
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

from prometheus_client import REGISTRY
from src.rag_core import offline_rag as offline_rag_module
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
async def test_get_context_trace_metadata_is_bounded(monkeypatch):
    metadata_by_span = {}
    inputs_by_span = {}

    class Observation:
        def __init__(self, name):
            self.name = name

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def update(self, *, metadata=None, **kwargs):
            assert not kwargs
            metadata_by_span[self.name] = dict(metadata or {})
            inputs_by_span[self.name] = kwargs

    class Client:
        def start_as_current_observation(self, *, as_type, name):
            assert as_type == "span"
            return Observation(name)

    class Retriever:
        async def ainvoke(self, _query):
            return [
                _FakeDoc("first"),
                _FakeDoc("first"),
                _FakeDoc("second"),
            ]

    class Reranker:
        backend = "openvino"

        def rerank(self, docs, _query):
            return docs

    monkeypatch.setattr(offline_rag_module, "get_langfuse_client", lambda: Client())
    rag = Offline_RAG(llm=object(), retriever=Retriever(), reranker=Reranker())

    async def queries(query, _history):
        return [query, "related query"]

    monkeypatch.setattr(rag, "generate_queries", queries)
    await rag.get_context("CNN là gì?")

    assert metadata_by_span["hybrid_retrieval"] == {
        "query_count": 2,
        "raw_docs": 6,
    }
    assert metadata_by_span["dedupe"] == {
        "capped_docs": 6,
        "unique_docs": 2,
    }
    assert metadata_by_span["rag_rerank"] == {
        "rerank_input_docs": 2,
        "rerank_output_docs": 2,
        "rerank_backend": "openvino",
    }
    assert metadata_by_span["format_context"]["context_chars"] > 0
    assert all(not values for values in inputs_by_span.values())


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
async def test_get_context_deduplicates_by_content_not_hash_value():
    class CollidingText(str):
        def __hash__(self):
            return 1

    class Retriever:
        async def ainvoke(self, _query):
            return [
                _FakeDoc(CollidingText("first")),
                _FakeDoc(CollidingText("second")),
            ]

    class Reranker:
        def rerank(self, docs, _query):
            return docs

    rag = Offline_RAG(llm=object(), retriever=Retriever(), reranker=Reranker())

    payload = json.loads(
        await rag.get_context("CNN là gì?", expand_query=False)
    )

    assert [item["content"] for item in payload] == ["first", "second"]

@pytest.mark.anyio
async def test_get_context_skips_query_expansion_when_disabled(monkeypatch):
    retrieved_queries = []

    class Retriever:
        async def ainvoke(self, query):
            retrieved_queries.append(query)
            return [_FakeDoc("direct context")]

    class Reranker:
        def rerank(self, docs, _query):
            return docs

    rag = Offline_RAG(llm=object(), retriever=Retriever(), reranker=Reranker())

    async def forbidden_expansion(*_args, **_kwargs):
        raise AssertionError("generate_queries must not run")

    monkeypatch.setattr(rag, "generate_queries", forbidden_expansion)
    labels = {"decision": "skip"}
    before = (
        REGISTRY.get_sample_value(
            "puq_rag_query_expansion_decisions_total",
            labels=labels,
        )
        or 0
    )
    payload = json.loads(await rag.get_context(
        "decision tree là gì",
        expand_query=False,
    ))

    assert retrieved_queries == ["decision tree là gì"]
    assert payload[0]["content"] == "direct context"
    assert (
        REGISTRY.get_sample_value(
            "puq_rag_query_expansion_decisions_total",
            labels=labels,
        )
        or 0
    ) == before + 1


@pytest.mark.anyio
async def test_get_context_defaults_to_approved_top_k_without_override(monkeypatch):
    class Retriever:
        async def ainvoke(self, _query):
            return [_FakeDoc(f"doc-{index}") for index in range(12)]

    class Reranker:
        def rerank(self, docs, _query):
            return docs

    monkeypatch.delenv("RAG_CONTEXT_TOP_K", raising=False)
    rag = Offline_RAG(llm=object(), retriever=Retriever(), reranker=Reranker())
    payload = json.loads(await rag.get_context(
        "decision tree là gì",
        expand_query=False,
    ))

    assert len(payload) == 5
    assert payload[0]["content"] == "doc-0"


@pytest.mark.parametrize(
    ("configured_top_k", "expected_top_k"),
    [("10", 10), ("7", 7), ("5", 5), ("0", 5), ("invalid", 5)],
)
@pytest.mark.anyio
async def test_get_context_respects_context_top_k(
    monkeypatch,
    configured_top_k,
    expected_top_k,
):
    class Retriever:
        async def ainvoke(self, _query):
            return [_FakeDoc(f"doc-{index}") for index in range(12)]

    class Reranker:
        def rerank(self, docs, _query):
            return docs

    monkeypatch.setenv("RAG_CONTEXT_TOP_K", configured_top_k)
    rag = Offline_RAG(llm=object(), retriever=Retriever(), reranker=Reranker())
    payload = json.loads(await rag.get_context(
        "decision tree là gì",
        expand_query=False,
    ))

    assert len(payload) == expected_top_k
    assert payload[0]["content"] == "doc-0"


@pytest.mark.anyio
async def test_get_context_caps_reranker_candidates_at_approved_limit(
    monkeypatch,
):
    captured = []

    class Retriever:
        async def ainvoke(self, query):
            return [
                _FakeDoc(f"{query}-doc-{index}")
                for index in range(30)
            ]

    class Reranker:
        backend = "openvino"

        def rerank(self, docs, _query):
            captured.extend(docs)
            return docs

    monkeypatch.setenv("RAG_RERANK_CANDIDATE_LIMIT", "24")

    rag = Offline_RAG(llm=object(), retriever=Retriever(), reranker=Reranker())

    async def expanded_queries(_query, _history):
        return ["query-a", "query-b"]

    monkeypatch.setattr(rag, "generate_queries", expanded_queries)

    payload = json.loads(
        await rag.get_context("decision tree là gì")
    )

    assert len(captured) == 24
    assert [doc.page_content for doc in captured] == [
        *[f"query-a-doc-{index}" for index in range(15)],
        *[f"query-b-doc-{index}" for index in range(9)],
    ]
    assert len(payload) == 5
    assert all(
        set(item)
        == {
            "video_url",
            "filename",
            "title",
            "start_timestamp",
            "end_timestamp",
            "content",
        }
        for item in payload
    )


@pytest.mark.anyio
async def test_get_context_records_reranker_input_document_count():
    class Retriever:
        async def ainvoke(self, _query):
            return [_FakeDoc(f"doc-{index}") for index in range(3)]

    class Reranker:
        backend = "openvino"

        def rerank(self, docs, _query):
            return docs

    labels = {"backend": "openvino"}
    before_count = (
        REGISTRY.get_sample_value(
            "puq_rag_rerank_input_documents_count",
            labels=labels,
        )
        or 0
    )
    before_sum = (
        REGISTRY.get_sample_value(
            "puq_rag_rerank_input_documents_sum",
            labels=labels,
        )
        or 0
    )
    rag = Offline_RAG(llm=object(), retriever=Retriever(), reranker=Reranker())

    await rag.get_context("decision tree là gì", expand_query=False)

    assert (
        REGISTRY.get_sample_value(
            "puq_rag_rerank_input_documents_count",
            labels=labels,
        )
        or 0
    ) == before_count + 1
    assert (
        REGISTRY.get_sample_value(
            "puq_rag_rerank_input_documents_sum",
            labels=labels,
        )
        or 0
    ) == before_sum + 3

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
