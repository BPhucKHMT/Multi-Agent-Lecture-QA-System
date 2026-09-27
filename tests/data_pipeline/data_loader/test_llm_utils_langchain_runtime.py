import importlib
import sys
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))


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
