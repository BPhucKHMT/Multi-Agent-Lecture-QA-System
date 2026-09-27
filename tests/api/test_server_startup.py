import os
import sys
import asyncio
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

from backend.app import main


@pytest.fixture(autouse=True)
def _disable_optional_observability(monkeypatch):
    monkeypatch.setattr(main, "initialize_langfuse", lambda: None)
    monkeypatch.delenv("PUQ_METRICS_ENABLED", raising=False)


def test_lifespan_prewarm_runs_in_background(monkeypatch):
    async def exercise():
        rag_called = asyncio.Event()

        def fake_prewarm():
            rag_called.set()

        monkeypatch.setattr(
            "src.rag_core.resource_manager.prewarm_all_resources", fake_prewarm
        )
        monkeypatch.setattr(
            "backend.app.models.user.Base.metadata.create_all",
            lambda *args, **kwargs: None,
        )
        monkeypatch.setattr(main.settings, "SEMANTIC_CACHE_ENABLED", False)

        async with main.lifespan(main.app):
            await asyncio.wait_for(rag_called.wait(), timeout=1)
        assert rag_called.is_set()

    asyncio.run(exercise())


def test_lifespan_closes_managed_jev_client(monkeypatch):
    from src.generation import jev_router

    created_clients = []
    original_client = jev_router.httpx.AsyncClient

    def build_client(**kwargs):
        client = original_client(**kwargs)
        created_clients.append(client)
        return client

    monkeypatch.setattr(jev_router.httpx, "AsyncClient", build_client)
    monkeypatch.setattr(main.Base.metadata, "create_all", lambda *args, **kwargs: None)
    monkeypatch.setattr(main.settings, "SEMANTIC_CACHE_ENABLED", False)
    monkeypatch.setattr(
        "src.rag_core.resource_manager.prewarm_all_resources",
        lambda: None,
    )

    async def exercise_lifespan():
        async with main.lifespan(main.app):
            assert len(created_clients) == 1
            assert not created_clients[0].is_closed

    asyncio.run(exercise_lifespan())
    assert created_clients[0].is_closed
