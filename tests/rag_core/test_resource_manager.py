import importlib
import os
import sys
from pathlib import Path

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


def test_get_quiz_resources_builds_once(monkeypatch):
    rm = importlib.reload(resource_manager)
    fake_retriever = object()
    fake_reranker = object()
    calls = {"count": 0}

    def _fake_build_quiz_resources():
        calls["count"] += 1
        return fake_retriever, fake_reranker

    monkeypatch.setattr(rm, "_build_quiz_resources", _fake_build_quiz_resources)

    first = rm.get_quiz_resources()
    second = rm.get_quiz_resources()

    assert first == (fake_retriever, fake_reranker)
    assert second == (fake_retriever, fake_reranker)
    assert calls["count"] == 1
