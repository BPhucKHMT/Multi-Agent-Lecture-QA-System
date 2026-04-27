import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

from src.api import server


def test_startup_prewarm_calls_resource_manager(monkeypatch):
    calls = {"count": 0}

    def _fake_prewarm():
        calls["count"] += 1

    monkeypatch.setattr(server.resource_manager, "prewarm_all_resources", _fake_prewarm)

    server.prewarm_rag_resources()

    assert calls["count"] == 1


def test_app_registers_startup_prewarm_handler():
    assert server.prewarm_rag_resources in server.app.router.on_startup
