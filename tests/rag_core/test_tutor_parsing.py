import asyncio
import os
import sys
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

from src.rag_core.agents import tutor


class _EmptyOutputChain:
    async def ainvoke(self, _inputs):
        return AIMessage(content="")


class _FakeRagCore:
    def __init__(self):
        self.context_calls = []

    async def get_context(self, query, chat_history="", expand_query=True):
        self.context_calls.append({
            "query": query,
            "chat_history": chat_history,
            "expand_query": expand_query,
        })
        return "[]"

    def get_answer_chain(self):
        return _EmptyOutputChain()




def test_node_tutor_handles_empty_output_with_clear_error(monkeypatch):
    monkeypatch.setattr(tutor.resource_manager, "get_rag_core", _FakeRagCore)

    result = asyncio.run(tutor.node_tutor({
        "messages": [HumanMessage(content="resnet là gì")]
    }))

    assert result["response"]["type"] == "error"
    assert "output rỗng" in result["response"]["text"]


def test_node_tutor_passes_expansion_decision_to_rag_core(monkeypatch):
    rag_core = _FakeRagCore()
    monkeypatch.setattr(tutor.resource_manager, "get_rag_core", lambda: rag_core)

    asyncio.run(tutor.node_tutor({
        "messages": [HumanMessage(content="decision tree là gì")],
        "tool_calls": [{
            "name": "AskTutor",
            "args": {
                "query": "decision tree là gì",
                "expand_query": False,
            },
        }],
    }))

    assert rag_core.context_calls[0]["expand_query"] is False


def test_node_tutor_does_not_expose_internal_exception_details(monkeypatch):
    class FailingRagCore:
        async def get_context(self, *_args, **_kwargs):
            raise RuntimeError("secret-token-canary")

    monkeypatch.setattr(
        tutor.resource_manager,
        "get_rag_core",
        lambda: FailingRagCore(),
    )

    result = asyncio.run(
        tutor.node_tutor(
            {"messages": [HumanMessage(content="decision tree là gì")]}
        )
    )

    assert result["response"]["type"] == "error"
    assert result["response"]["text"] == "Không thể xử lý câu hỏi lúc này."
    assert "secret-token-canary" not in result["response"]["text"]

def test_sync_citation_metadata_backfills_missing_entries_from_context():
    response = {
        "text": "Attention dùng Query, Key, Value [0][3].",
        "video_url": ["https://youtube.com/watch?v=a"],
        "title": ["Part 1"],
        "filename": ["a.json"],
        "start_timestamp": ["00:00:01"],
        "end_timestamp": ["00:00:10"],
        "confidence": ["high"],
    }
    context = """
    [
      {
        "video_url": "https://youtube.com/watch?v=a",
        "title": "Part 1",
        "filename": "a.json",
        "start_timestamp": "00:00:01",
        "end_timestamp": "00:00:10",
        "content": "doc 0"
      },
      {},
      {},
      {
        "video_url": "https://youtube.com/watch?v=d",
        "title": "Part 4: Key Value",
        "filename": "d.json",
        "start_timestamp": "00:08:09",
        "end_timestamp": "00:09:00",
        "content": "doc 3"
      }
    ]
    """

    synced = tutor._sync_citation_metadata_from_context(response, context)

    assert synced["video_url"][3] == "https://youtube.com/watch?v=d"
    assert synced["title"][3] == "Part 4: Key Value"
    assert synced["start_timestamp"][3] == "00:08:09"
    assert synced["confidence"][3] == "medium"
