import importlib
import sys
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))


def test_call_llm_api_uses_chatopenai(monkeypatch):
    captured = {"kwargs": {}, "messages": None}

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs

        def invoke(self, messages):
            captured["messages"] = messages
            return types.SimpleNamespace(content="  da sua  ")

    monkeypatch.setitem(
        sys.modules,
        "langchain_openai",
        types.SimpleNamespace(ChatOpenAI=FakeChatOpenAI),
    )
    monkeypatch.setenv("myAPIKey", "unit-test-key")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    module = importlib.import_module("src.data_pipeline.data_loader.llm_utils")
    importlib.reload(module)
    result = module.call_llm_api("noi dung can sua", "he thong")

    assert captured["kwargs"]["api_key"] == "unit-test-key"
    assert captured["kwargs"]["model"] == "gpt-5-mini"
    assert result == "da sua"


def test_call_llm_api_requires_myapikey(monkeypatch):
    monkeypatch.setenv("myAPIKey", "")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    module = importlib.import_module("src.data_pipeline.data_loader.llm_utils")
    importlib.reload(module)

    try:
        module.call_llm_api("abc", "sys")
        assert False, "Expected ValueError when myAPIKey is missing"
    except ValueError as exc:
        assert "myAPIKey" in str(exc)
