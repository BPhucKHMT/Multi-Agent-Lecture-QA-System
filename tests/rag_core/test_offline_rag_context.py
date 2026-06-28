import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

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


class _FakeRetriever:
    def __init__(self, docs):
        self.docs = docs

    def invoke(self, _query):
        return self.docs


class _FakeReranker:
    def __init__(self):
        self.received_top_k = None

    def rerank(self, docs, _query, top_k):
        self.received_top_k = top_k
        return docs[:top_k]


def test_get_context_passes_top_k_and_truncates_content():
    docs = [_FakeDoc("A" * 5000), _FakeDoc("B" * 5000)]
    reranker = _FakeReranker()
    rag = Offline_RAG(llm=object(), retriever=_FakeRetriever(docs), reranker=reranker)

    context = rag.get_context("cnn la gi")
    payload = json.loads(context)

    assert reranker.received_top_k == 10
    assert len(payload) == 2
    assert all(len(item["content"]) <= 1000 for item in payload)


def test_offline_rag_prompt_is_compact_to_avoid_token_bloat():
    rag = Offline_RAG(llm=object(), retriever=_FakeRetriever([]), reranker=_FakeReranker())
    template = rag.prompt.messages[0].prompt.template
    assert len(template) <= 2000


def test_get_context_total_serialized_size_is_capped():
    docs = [_FakeDoc("X" * 20000) for _ in range(20)]
    reranker = _FakeReranker()
    rag = Offline_RAG(llm=object(), retriever=_FakeRetriever(docs), reranker=reranker)

    context = rag.get_context("linear regression là gì")

    assert len(context) <= 6000
