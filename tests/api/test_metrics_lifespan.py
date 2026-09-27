import asyncio
import os
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

from backend.app import main
from src.shared.metrics import CHAT_ACTIVE, CHAT_REQUESTS


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _port_is_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        try:
            listener.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _scrape(port: int) -> str:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=1) as response:
        return response.read().decode("utf-8")


async def _wait_for_scrape(port: int) -> str:
    deadline = asyncio.get_running_loop().time() + 2
    while True:
        try:
            return await asyncio.to_thread(_scrape, port)
        except (OSError, urllib.error.URLError):
            if asyncio.get_running_loop().time() >= deadline:
                raise
            await asyncio.sleep(0.01)


def _patch_lightweight_startup(monkeypatch) -> None:
    monkeypatch.setattr(main.Base.metadata, "create_all", lambda *args, **kwargs: None)
    monkeypatch.setattr(main.settings, "SEMANTIC_CACHE_ENABLED", False)
    monkeypatch.setattr(main, "initialize_langfuse", lambda: None)
    monkeypatch.setattr(
        "src.rag_core.resource_manager.prewarm_all_resources",
        lambda: None,
    )


def test_enabled_metrics_exporter_scrapes_and_releases_port(monkeypatch):
    _patch_lightweight_startup(monkeypatch)
    monkeypatch.setenv("PUQ_METRICS_ENABLED", "true")
    monkeypatch.setenv("PUQ_METRICS_BIND_HOST", "127.0.0.1")

    async def exercise():
        for _ in range(2):
            port = _free_port()
            monkeypatch.setenv("PUQ_METRICS_PORT", str(port))

            async with main.lifespan(main.app):
                CHAT_REQUESTS.labels("direct", "success", "miss").inc()
                CHAT_ACTIVE.inc()
                CHAT_ACTIVE.dec()
                payload = await _wait_for_scrape(port)
                assert "puq_chat_requests_total" in payload
                assert "puq_chat_active" in payload

            assert _port_is_available(port)

    asyncio.run(exercise())


def test_disabled_metrics_do_not_expose_public_api_metrics(monkeypatch):
    import httpx

    _patch_lightweight_startup(monkeypatch)
    monkeypatch.delenv("PUQ_METRICS_ENABLED", raising=False)
    monkeypatch.delenv("PUQ_METRICS_PORT", raising=False)

    async def exercise():
        async with main.lifespan(main.app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=main.app), base_url="http://test"
            ) as client:
                return await client.get("/metrics")

    assert asyncio.run(exercise()).status_code == 404


def test_metrics_server_is_closed_when_startup_fails(monkeypatch):
    _patch_lightweight_startup(monkeypatch)
    port = _free_port()
    monkeypatch.setenv("PUQ_METRICS_ENABLED", "true")
    monkeypatch.setenv("PUQ_METRICS_BIND_HOST", "127.0.0.1")
    monkeypatch.setenv("PUQ_METRICS_PORT", str(port))

    def fail_database_startup(*args, **kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(main.Base.metadata, "create_all", fail_database_startup)

    async def exercise():
        async with main.lifespan(main.app):
            pass

    with pytest.raises(RuntimeError, match="database unavailable"):
        asyncio.run(exercise())

    assert _port_is_available(port)
