import os
import sys
import asyncio
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

from backend.app import main


@pytest.mark.asyncio
async def test_lifespan_prewarm_runs_in_background(monkeypatch):
    rag_called = asyncio.Event()

    def _fake_prewarm():
        rag_called.set()

    # Mock the prewarm_all_resources function to avoid loading actual heavy models/DB
    monkeypatch.setattr("src.rag_core.resource_manager.prewarm_all_resources", _fake_prewarm)
    
    # Disable database creation during test to prevent side effects
    monkeypatch.setattr("backend.app.models.user.Base.metadata.create_all", lambda *args, **kwargs: None)
    
    # Disable semantic cache prewarm for simplicity in this test
    monkeypatch.setattr(main.settings, "SEMANTIC_CACHE_ENABLED", False)

    # Execute lifespan as an async context manager
    async with main.lifespan(main.app):
        # Wait up to 1 second for the background task to trigger the mock
        try:
            await asyncio.wait_for(rag_called.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            pytest.fail("RAG prewarm background task was not scheduled/executed during lifespan startup.")

    assert rag_called.is_set()
