import asyncio
import os
import sys
import uuid
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

from src.shared import observability


from langfuse import Langfuse

try:
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )
except ImportError:
    from opentelemetry.sdk.trace.export import InMemorySpanExporter

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider


@pytest.fixture(autouse=True)
def _reset_observability_client(monkeypatch):
    monkeypatch.setattr(observability, "_LANGFUSE_CLIENT", None)


def _configured_env(monkeypatch, *, base_url="http://langfuse.test"):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    monkeypatch.setenv("LANGFUSE_BASE_URL", base_url)
    monkeypatch.setenv("LANGFUSE_TRACING_ENABLED", "true")


def _capture_spans():
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    client = Langfuse(
        public_key=f"pk-{uuid.uuid4().hex}",
        secret_key="sk-test",
        base_url="http://langfuse.test",
        tracer_provider=provider,
        span_exporter=exporter,
        flush_at=1,
        mask_otel_spans=observability.mask_otel_spans,
    )
    try:
        tracer = provider.get_tracer("opentelemetry.instrumentation.langchain")
        with client.start_as_current_observation(
            name="chat_stream", as_type="span"
        ):
            root = trace.get_current_span()
            root.set_attribute(observability._ROOT_MARKER, True)
            root.set_attribute("gen_ai.prompt.0.content", "prompt-canary")
            root.set_attribute("gen_ai.completion.0.content", "answer-canary")
            root.set_attribute(
                "http.request.header.authorization", "header-canary"
            )
            root.set_attribute("exception.message", "exception-canary")
            root.set_attribute(
                "langfuse.observation.metadata.route", "tutor"
            )
            root.set_attribute(
                "langfuse.observation.metadata.model", "jev-latest"
            )
            root.set_attribute(
                "langfuse.observation.metadata.untrusted", "metadata-canary"
            )
            root.set_attribute(
                "langfuse.observation.output",
                '{"answer":"safe-answer-canary", "api_key":"secret-key-canary"}',
            )
            with tracer.start_as_current_span("chat_stream") as child:
                child.set_attribute("gen_ai.prompt.0.content", "child-prompt-canary")
                child.set_attribute("gen_ai.completion.0.content", "child-answer-canary")
                child.set_attribute(
                    "langfuse.observation.output", "child-output-canary"
                )
                child.set_attribute(
                    "langfuse.observation.metadata.model", "raw-model-canary"
                )
        client.flush()
        return list(exporter.get_finished_spans())
    finally:
        client.shutdown()


def test_actual_sdk_export_hook_redacts_callback_attributes(monkeypatch):
    _configured_env(monkeypatch)
    monkeypatch.delenv("PUQ_TRACE_CONTENT", raising=False)
    spans = _capture_spans()
    serialized = repr([dict(span.attributes) for span in spans])

    for canary in (
        "prompt-canary",
        "answer-canary",
        "child-prompt-canary",
        "child-answer-canary",
        "header-canary",
        "exception-canary",
        "metadata-canary",
        "safe-answer-canary",
        "secret-key-canary",
        "child-output-canary",
        "raw-model-canary",
    ):
        assert canary not in serialized

    assert any(
        span.attributes.get("langfuse.observation.metadata.route") == "tutor"
        for span in spans
    )
    assert any(
        span.attributes.get("langfuse.observation.metadata.model") == "jev-latest"
        for span in spans
    )


def test_actual_sdk_export_hook_allows_only_root_output_with_token_key_mask(
    monkeypatch,
):
    _configured_env(monkeypatch)
    monkeypatch.setenv("PUQ_TRACE_CONTENT", "true")
    spans = _capture_spans()
    serialized = repr([dict(span.attributes) for span in spans])

    assert "safe-answer-canary" in serialized
    assert "secret-key-canary" not in serialized
    assert "child-output-canary" not in serialized
    assert "child-prompt-canary" not in serialized


def test_disabled_configuration_does_not_construct_or_lazy_init(monkeypatch):
    called = []

    class SpyLangfuse:
        def __init__(self, **kwargs):
            called.append(kwargs)

    monkeypatch.setattr(observability, "Langfuse", SpyLangfuse)
    for name in (
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_BASE_URL",
        "LANGFUSE_TRACING_ENABLED",
    ):
        monkeypatch.delenv(name, raising=False)

    assert observability.get_langfuse_client() is None
    assert observability.initialize_langfuse() is None
    assert called == []


def test_enabled_configuration_initializes_one_masked_singleton(monkeypatch):
    calls = []

    class FakeLangfuse:
        def __init__(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(observability, "Langfuse", FakeLangfuse)
    _configured_env(monkeypatch)

    first = observability.initialize_langfuse()
    second = observability.initialize_langfuse()

    assert first is second
    assert len(calls) == 1
    assert calls[0]["mask_otel_spans"] is observability.mask_otel_spans
    assert calls[0]["tracing_enabled"] is True


def test_shutdown_allows_same_key_client_to_export_after_restart(monkeypatch):
    _configured_env(monkeypatch)
    created = []

    def build_client(**kwargs):
        provider = TracerProvider()
        exporter = InMemorySpanExporter()
        client = Langfuse(
            **kwargs,
            tracer_provider=provider,
            span_exporter=exporter,
            flush_at=1,
        )
        created.append((client, exporter))
        return client

    monkeypatch.setattr(observability, "Langfuse", build_client)

    for _ in range(2):
        client = observability.initialize_langfuse()
        assert client is not None
        with client.start_as_current_observation(
            name="chat_stream", as_type="span"
        ):
            trace.get_current_span().set_attribute(
                "langfuse.observation.metadata.route", "tutor"
            )
        client.flush()
        observability.shutdown_langfuse()

    assert len(created) == 2
    assert all(exporter.get_finished_spans() for _, exporter in created)


def test_trace_content_requires_enabled_keys_and_supports_cloud(monkeypatch):
    _configured_env(monkeypatch, base_url="https://cloud.langfuse.com")
    monkeypatch.setenv("PUQ_TRACE_CONTENT", "true")
    assert observability.trace_content_enabled() is True

    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://langfuse.internal.example")
    assert observability.trace_content_enabled() is True

    monkeypatch.setenv("LANGFUSE_TRACING_ENABLED", "false")
    assert observability.trace_content_enabled() is False

def test_real_langgraph_stream_keeps_model_children_and_masks_contents():
    from typing import TypedDict

    from langchain_core.language_models.fake_chat_models import FakeListChatModel
    from langchain_core.messages import HumanMessage
    from langchain_core.runnables import RunnableConfig
    from langfuse.langchain import CallbackHandler
    from langgraph.graph import END, START, StateGraph

    class ChatState(TypedDict):
        messages: list
        answer: str

    model = FakeListChatModel(responses=["answer-canary-s3cr3t"])

    async def answer(state: ChatState, config: RunnableConfig):
        response = await model.ainvoke(state["messages"], config=config)
        return {"answer": response.content}

    builder = StateGraph(ChatState)
    builder.add_node("direct", answer)
    builder.add_edge(START, "direct")
    builder.add_edge("direct", END)
    graph = builder.compile()

    async def exercise(client, public_key):
        events = []
        with client.start_as_current_observation(as_type="span", name="chat_stream"):
            async for event in graph.astream_events(
                {"messages": [HumanMessage(content="prompt-canary-s3cr3t")]},
                version="v2",
                config={"callbacks": [CallbackHandler(public_key=public_key)]},
            ):
                events.append(event["event"])
        return events

    exporter = InMemorySpanExporter()
    public_key = f"pk-{uuid.uuid4().hex}"
    client = Langfuse(
        public_key=public_key,
        secret_key="sk-test",
        base_url="http://langfuse.test",
        tracer_provider=TracerProvider(),
        span_exporter=exporter,
        mask_otel_spans=observability.mask_otel_spans,
        flush_at=1,
    )
    try:
        events = asyncio.run(exercise(client, public_key))
        client.flush()
        spans = exporter.get_finished_spans()
        root = next(span for span in spans if span.name == "chat_stream")
        descendants = [span for span in spans if span.name != root.name]
        assert descendants
        assert all(span.context.trace_id == root.context.trace_id for span in descendants)
        assert any(span.parent and span.parent.span_id == root.context.span_id for span in descendants)
        assert "on_chat_model_stream" in events
        serialized = repr([dict(span.attributes) for span in spans])
        assert "prompt-canary-s3cr3t" not in serialized
        assert "answer-canary-s3cr3t" not in serialized
    finally:
        client.shutdown()


def test_jev_trace_has_one_supervisor_child_without_private_contents(monkeypatch):
    from langchain_core.messages import HumanMessage
    from langfuse.langchain import CallbackHandler
    import httpx
    from langgraph.graph import END, START, StateGraph
    from src.generation import jev_router
    from src.rag_core import lang_graph_rag
    from src.rag_core.state import State

    monkeypatch.setenv("EXPERIENTIAL_API_KEY", "xpl-test")
    monkeypatch.setattr(jev_router, "_jev_http_client", None)
    original_client = httpx.AsyncClient

    def make_client(**kwargs):
        return original_client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={"answers": {"route": {"choice": "AskGeneral"}}},
                )
            ),
            **kwargs,
        )

    monkeypatch.setattr(jev_router.httpx, "AsyncClient", make_client)
    graph_builder = StateGraph(State)
    graph_builder.add_node("supervisor", lang_graph_rag.node_supervisor)
    graph_builder.add_edge(START, "supervisor")
    graph_builder.add_edge("supervisor", END)
    graph = graph_builder.compile()

    exporter = InMemorySpanExporter()
    public_key = f"pk-{uuid.uuid4().hex}"
    client = Langfuse(
        public_key=public_key,
        secret_key="sk-test",
        base_url="http://langfuse.test",
        tracer_provider=TracerProvider(),
        span_exporter=exporter,
        mask_otel_spans=observability.mask_otel_spans,
        flush_at=1,
    )

    async def exercise():
        with client.start_as_current_observation(as_type="span", name="chat_stream"):
            return await graph.ainvoke(
                {"messages": [HumanMessage(content="Xin chào")]},
                config={"callbacks": [CallbackHandler(public_key=public_key)]},
            )

    try:
        result = asyncio.run(exercise())
        client.flush()
        spans = exporter.get_finished_spans()
        supervisors = [span for span in spans if span.name == "supervisor"]
        jev_spans = [span for span in spans if span.name == "jev_supervisor"]
        assert len(supervisors) == len(jev_spans) == 1
        assert not any(span.name == "jev_http_request" for span in spans)
        assert jev_spans[0].parent.span_id == supervisors[0].context.span_id
        assert jev_spans[0].attributes["langfuse.observation.metadata.model"] == "jev-latest"
        assert result["tool_calls"][0]["name"] == "AskGeneral"
        assert "Xin chào" not in repr(dict(jev_spans[0].attributes))
    finally:
        client.shutdown()
