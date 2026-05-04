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
