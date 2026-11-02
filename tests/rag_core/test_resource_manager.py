import importlib
import os
import sys
from pathlib import Path

from prometheus_client import REGISTRY
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

from src.rag_core import resource_manager


def test_get_rag_core_builds_once(monkeypatch):
    rm = importlib.reload(resource_manager)
    marker = object()
    calls = {"count": 0}

    def _fake_build_rag_core():
        calls["count"] += 1
        return marker

    monkeypatch.setattr(rm, "_build_rag_core", _fake_build_rag_core)

    assert rm.get_rag_core() is marker
    assert rm.get_rag_core() is marker
    assert calls["count"] == 1

def test_get_reranker_singleton(monkeypatch):
    rm = importlib.reload(resource_manager)
    marker = object()
    calls = {"count": 0}

    def _fake_build_reranker():
        calls["count"] += 1
        return marker

    monkeypatch.setattr(rm, "_build_reranker", _fake_build_reranker)

    assert rm.get_reranker() is marker
    assert calls["count"] == 1


def test_prewarm_runs_local_retrieval_and_reranker(monkeypatch):
    rm = importlib.reload(resource_manager)

    class Retriever:
        def __init__(self):
            self.invoke_calls = []

        def invoke(self, query):
            self.invoke_calls.append(query)
            return ["Tài liệu khởi động cho bộ tái xếp hạng."]

    class Reranker:
        def __init__(self):
            self.score_calls = []

        def score_pairs(self, query, passages):
            self.score_calls.append((query, list(passages)))
            return [0.5 for _ in passages]

    retriever = Retriever()
    reranker = Reranker()
    monkeypatch.setattr(rm, "get_rag_core", lambda: object())
    monkeypatch.setattr(rm, "get_vector_retriever", lambda: retriever)
    monkeypatch.setattr(rm, "get_reranker", lambda: reranker)

    rm.prewarm_all_resources()

    assert retriever.invoke_calls == ["khởi động hệ thống"]
    assert reranker.score_calls == [
        (
            "khởi động hệ thống",
            ["Tài liệu khởi động cho bộ tái xếp hạng."],
        )
    ]
    assert REGISTRY.get_sample_value("puq_rag_prewarm_ready") == 1.0

