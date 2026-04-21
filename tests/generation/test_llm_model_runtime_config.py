import importlib
import sys
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def test_get_llm_uses_myapikey_and_gpt5mini(monkeypatch):
    captured = {}

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setitem(sys.modules, "langchain_openai", types.SimpleNamespace(ChatOpenAI=FakeChatOpenAI))
    monkeypatch.setenv("myAPIKey", "unit-test-key")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    module = importlib.import_module("src.generation.llm_model")
    importlib.reload(module)
    module.get_llm()

    assert captured["api_key"] == "unit-test-key"
    assert captured["model"] == "gpt-5-mini"
    assert "base_url" not in captured
