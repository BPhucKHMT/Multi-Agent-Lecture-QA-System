import os
import sys
from pathlib import Path

from langchain_core.messages import HumanMessage

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

from src.rag_core.agents import tutor


class _EmptyOutputChain:
    def invoke(self, _query):
        return type("LLMResult", (), {"content": ""})()


def test_get_rag_chain_delegates_to_resource_manager(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(tutor.resource_manager, "get_tutor_chain", lambda: sentinel)

    assert tutor.get_rag_chain() is sentinel


def test_node_tutor_handles_empty_output_with_clear_error(monkeypatch):
    monkeypatch.setattr(tutor, "get_rag_chain", lambda: _EmptyOutputChain())

    result = tutor.node_tutor({"messages": [HumanMessage(content="resnet là gì")]})

    assert result["response"]["type"] == "error"
    assert "output rỗng" in result["response"]["text"]
    assert "Expecting value" not in result["response"]["text"]
