import os
import sys
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

from src.generation import llm_model


def test_get_supervisor_llm_uses_reduced_default_max_tokens(monkeypatch):
    captured = {}

    class _FakeChatOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    fake_module = types.SimpleNamespace(ChatOpenAI=_FakeChatOpenAI)
    monkeypatch.setitem(sys.modules, "langchain_openai", fake_module)
    monkeypatch.delenv("OPENAI_SUPERVISOR_MAX_TOKENS", raising=False)

    llm_model.get_supervisor_llm()

    assert captured["max_tokens"] == 256
