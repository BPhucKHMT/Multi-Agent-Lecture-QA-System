import asyncio
import builtins
import json
import os
import sys
import hashlib
import uuid
import time
import threading
from types import SimpleNamespace
import numpy as np
from pathlib import Path
import pytest
from prometheus_client import REGISTRY
from langchain_core.messages import AIMessage

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))
from src.shared import metrics as shared_metrics

from backend.app.services import chat as chat_service
from backend.app.core.cache import semantic as semantic_cache_module
from backend.app.models.user import ChatHistory
from backend.app.core.cache.semantic import (
    SemanticCache,
    should_use_candidate,
    is_response_cacheable,
    is_cache_lookup_allowed,
    normalize_query,
    same_intent,
    keyword_overlap,
)


class _MockQuery:
    def __init__(self, results=None):
        self.results = results or []

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        return self.results


class _MockDBSession:
    def __init__(self, query_results=None):
        self.query_results = query_results or []
        self.added_items = []
        self.committed = False

    def query(self, model):
        return _MockQuery(self.query_results)

    def add(self, item):
        self.added_items.append(item)

    def commit(self):
        self.committed = True


async def _collect_stream(gen):
    chunks = []
    async for item in gen:
        chunks.append(item)
    return chunks

def test_stream_telemetry_deduplicates_model_usage_by_run_id():
    telemetry = chat_service._StreamTelemetry()
    first = {
        "run_id": "generation-1",
        "data": {
            "output": AIMessage(
                content="answer",
                usage_metadata={
                    "input_tokens": 120,
                    "output_tokens": 30,
                    "total_tokens": 150,
                },
            )
        },
    }
    duplicate = dict(first)
    second = {
        "run_id": "generation-2",
        "data": {
            "output": AIMessage(
                content="internal",
                usage_metadata={
                    "input_tokens": 20,
                    "output_tokens": 5,
                    "total_tokens": 25,
                },
            )
        },
    }

    telemetry.record_model_usage(first)
    telemetry.record_model_usage(duplicate)
    telemetry.record_model_usage(second)

    assert telemetry.llm_input_tokens == 140
    assert telemetry.llm_output_tokens == 35
    assert telemetry.llm_total_tokens == 175
    assert telemetry.llm_generation_count == 2


def test_usage_metadata_is_fail_safe_and_preserves_total_invariant():
    malformed = SimpleNamespace(
        usage_metadata={
            "input_tokens": "invalid",
            "output_tokens": None,
            "total_tokens": -3,
        }
    )
    missing_total = SimpleNamespace(
        usage_metadata={
            "input_tokens": 20,
            "output_tokens": 5,
            "total_tokens": 0,
        }
    )

    assert chat_service._extract_usage_metadata(malformed) == {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
    }
    assert chat_service._extract_usage_metadata(missing_total) == {
        "input_tokens": 20,
        "output_tokens": 5,
        "total_tokens": 25,
    }



def test_chat_stage_metric_failure_does_not_break_request(monkeypatch):
    class BrokenMetric:
        def labels(self, **_labels):
            return self

        def observe(self, _value):
            raise RuntimeError("metrics unavailable")

    monkeypatch.setattr(shared_metrics, "CHAT_STAGE_DURATION", BrokenMetric())

    with shared_metrics.measure_chat_stage("history_load"):
        pass

def test_semantic_cache_get_keeps_event_loop_responsive():
    cache = SemanticCache.__new__(SemanticCache)
    started = threading.Event()
    release = threading.Event()

    def blocking_get(_prompt):
        started.set()
        release.wait(timeout=1)
        return {"text": "cached"}

    cache._get_sync = blocking_get

    async def exercise():
        lookup = asyncio.create_task(cache.get("query"))
        await asyncio.sleep(0.01)
        assert started.is_set()
        assert not lookup.done()
        release.set()
        return await asyncio.wait_for(lookup, timeout=1)

    assert asyncio.run(exercise()) == {"text": "cached"}


class _BrokenWorkflow:
    async def astream_events(self, *_args, **_kwargs):
        raise RuntimeError("secret-token-canary")
        yield  # pragma: no cover

    async def ainvoke(self, *_args, **_kwargs):
        return {"response": {"text": "fallback"}}


class _SingleRunWorkflow:
    def __init__(self):
        self.ainvoke_calls = 0

    async def astream_events(self, *_args, **_kwargs):
        class _Chunk:
            def __init__(self, content):
                self.content = content

        yield {
            "event": "on_chat_model_stream",
            "metadata": {"langgraph_node": "direct"},
            "tags": ["final_answer"],
            "data": {"chunk": _Chunk("Xin")},
        }
        yield {
            "event": "on_chain_end",
            "metadata": {"langgraph_node": "direct"},
            "data": {
                "output": {
                    "response": {
                        "text": "Xin chao",
                        "video_url": [],
                        "title": [],
                        "filename": [],
                        "start_timestamp": [],
                        "end_timestamp": [],
                        "confidence": [],
                        "type": "direct",
                    }
                }
            },
        }

    async def ainvoke(self, *_args, **_kwargs):
        self.ainvoke_calls += 1
        raise AssertionError("ainvoke should not be called in streaming path")


class _EmptyResponseWorkflow:
    async def astream_events(self, *_args, **_kwargs):
        yield {
            "event": "on_chain_end",
            "metadata": {"langgraph_node": "direct"},
            "data": {"output": {"response": {}}}
        }

    async def ainvoke(self, *_args, **_kwargs):
        return {"response": {}}


class _EmptyDirectPayloadWorkflow:
    async def astream_events(self, *_args, **_kwargs):
        yield {
            "event": "on_chain_end",
            "metadata": {"langgraph_node": "direct"},
            "data": {
                "output": {
                    "response": {
                        "text": "   ",
                        "video_url": [],
                        "title": [],
                        "filename": [],
                        "start_timestamp": [],
                        "end_timestamp": [],
                        "confidence": [],
                        "type": "direct",
                    }
                }
            },
        }

    async def ainvoke(self, *_args, **_kwargs):
        return {"response": {"text": "unused"}}


class _CaptureHistoryWorkflow:
    def __init__(self):
        self.captured_message_count = None
        self.captured_messages = []

    @staticmethod
    def _extract_role(message):
        message_type = getattr(message, "type", "")
        if message_type == "human":
            return "user"
        if message_type == "ai":
            return "assistant"
        return message_type or message.__class__.__name__

    async def astream_events(self, initial_state, *_args, **_kwargs):
        messages = initial_state.get("messages", [])
        self.captured_message_count = len(messages)
        self.captured_messages = [
            {
                "role": self._extract_role(message),
                "content": getattr(message, "content", None),
            }
            for message in messages
        ]
        yield {
            "event": "on_chain_end",
            "metadata": {"langgraph_node": "direct"},
            "data": {
                "output": {
                    "response": {
                        "text": "ok",
                        "video_url": [],
                        "title": [],
                        "filename": [],
                        "start_timestamp": [],
                        "end_timestamp": [],
                        "confidence": [],
                        "type": "direct",
                    }
                }
            },
        }

    async def ainvoke(self, *_args, **_kwargs):
        return {"response": {"text": "unused"}}


# --- Adapted Original Tests ---

def test_generate_stream_returns_error_metadata_when_streaming_fails(monkeypatch):
    monkeypatch.setattr(chat_service, "workflow", _BrokenWorkflow(), raising=False)
    db = _MockDBSession()

    chunks = asyncio.run(_collect_stream(chat_service.generate_chat_stream(db, "user-1", "conv-1", "tạo quiz cnn")))
    payloads = [c for c in chunks if c.startswith("data: ") and c != "data: [DONE]\n\n"]

    assert payloads, "Expected at least one SSE payload"
    body = json.loads(payloads[-1][6:])
    assert body["type"] == "error"
    assert body["content"] == "Lỗi xử lý câu hỏi. Vui lòng thử lại."
    assert chunks[-1] == "data: [DONE]\n\n"


def test_generate_stream_uses_single_workflow_execution(monkeypatch):
    workflow = _SingleRunWorkflow()
    monkeypatch.setattr(chat_service, "workflow", workflow, raising=False)
    db = _MockDBSession()

    chunks = asyncio.run(_collect_stream(chat_service.generate_chat_stream(db, "user-1", "conv-1", "tạo quiz cnn")))
    payloads = [c for c in chunks if c.startswith("data: ") and c != "data: [DONE]\n\n"]

    assert payloads, "Expected at least one SSE payload"
    body = json.loads(payloads[-1][6:])
    assert body["type"] == "metadata"
    assert body["response"]["type"] == "direct"
    assert body["response"]["text"] == "Xin chao"
    assert workflow.ainvoke_calls == 0
    assert chunks[-1] == "data: [DONE]\n\n"

def test_generate_stream_records_history_stage_metric(monkeypatch):
    monkeypatch.setattr(chat_service, "workflow", _SingleRunWorkflow(), raising=False)
    labels = {"stage": "history_load", "outcome": "success"}
    before = REGISTRY.get_sample_value(
        "puq_chat_stage_duration_seconds_count", labels=labels
    ) or 0

    asyncio.run(
        _collect_stream(
            chat_service.generate_chat_stream(
                _MockDBSession(), "user-1", "conv-1", "tạo quiz cnn"
            )
        )
    )

    after = REGISTRY.get_sample_value(
        "puq_chat_stage_duration_seconds_count", labels=labels
    ) or 0
    assert after == before + 1


def test_generate_stream_emits_token_before_metadata(monkeypatch):
    workflow = _SingleRunWorkflow()
    monkeypatch.setattr(chat_service, "workflow", workflow, raising=False)
    db = _MockDBSession()

    chunks = asyncio.run(_collect_stream(chat_service.generate_chat_stream(db, "user-1", "conv-1", "tạo quiz cnn")))
    payloads = [
        json.loads(c[6:])
        for c in chunks
        if c.startswith("data: ") and c != "data: [DONE]\n\n"
    ]

    assert payloads, "Expected SSE payloads"
    assert payloads[0]["type"] == "token"
    assert payloads[0]["content"] == "Xin"
    assert payloads[-1]["type"] == "metadata"
    assert payloads[-1]["response"]["type"] == "direct"


def test_generate_stream_returns_error_when_response_payload_is_empty(monkeypatch):
    monkeypatch.setattr(chat_service, "workflow", _EmptyResponseWorkflow(), raising=False)
    db = _MockDBSession()

    chunks = asyncio.run(_collect_stream(chat_service.generate_chat_stream(db, "user-1", "conv-1", "tạo quiz cnn")))
    payloads = [c for c in chunks if c.startswith("data: ") and c != "data: [DONE]\n\n"]

    assert payloads, "Expected at least one SSE payload"
    body = json.loads(payloads[-1][6:])
    assert body["type"] == "metadata"
    assert body["response"]["type"] == "error"
    assert "Không nhận được phản hồi từ AI" in body["response"]["text"]


def test_generate_stream_returns_error_when_direct_payload_text_is_empty(monkeypatch):
    monkeypatch.setattr(
        chat_service,
        "workflow",
        _EmptyDirectPayloadWorkflow(),
        raising=False,
    )
    db = _MockDBSession()

    chunks = asyncio.run(_collect_stream(chat_service.generate_chat_stream(db, "user-1", "conv-1", "tạo quiz cnn")))
    payloads = [c for c in chunks if c.startswith("data: ") and c != "data: [DONE]\n\n"]

    assert payloads, "Expected at least one SSE payload"
    body = json.loads(payloads[-1][6:])
    assert body["type"] == "metadata"
    assert body["response"]["type"] == "error"
    assert "Không nhận được phản hồi từ AI" in body["response"]["text"]


def test_generate_stream_caps_history_before_invoking_workflow(monkeypatch):
    workflow = _CaptureHistoryWorkflow()
    monkeypatch.setattr(chat_service, "workflow", workflow, raising=False)
    monkeypatch.setattr(chat_service, "MAX_HISTORY_MESSAGES", 4, raising=False)

    request_messages = []
    for i in range(12):
        role = "user" if i % 2 == 0 else "assistant"
        request_messages.append({"role": role, "content": f"msg-{i}"})

    db_history = [
        ChatHistory(user_id="user-1", session_id="conv-1", role=msg["role"], content=msg["content"])
        for msg in request_messages
    ]
    db = _MockDBSession(query_results=db_history)

    chunks = asyncio.run(_collect_stream(chat_service.generate_chat_stream(db, "user-1", "conv-1", "new-msg")))
    assert chunks[-1] == "data: [DONE]\n\n"
    expected_messages = [
        {"role": "user", "content": "msg-8"},
        {"role": "assistant", "content": "msg-9"},
        {"role": "user", "content": "msg-10"},
        {"role": "assistant", "content": "msg-11"},
        {"role": "user", "content": "new-msg"},
    ]
    assert workflow.captured_message_count == len(expected_messages)
    assert workflow.captured_messages == expected_messages


# --- New Semantic Cache Verification Tests ---

def test_chat_stream_cache_hit_saves_user_and_assistant_to_db(monkeypatch):
    """Kiểm thử cache hit vẫn lưu đủ user + assistant vào DB."""
    # Kích hoạt cache
    monkeypatch.setattr(chat_service, "SEMANTIC_CACHE_ENABLED", True)

    cached_response = {
        "text": "Đây là câu trả lời được lấy từ cache, rất nhanh chóng và chính xác.",
        "type": "rag",
        "video_url": ["https://youtube.com/watch?v=abcdef123"],
    }

    class FakeSemanticCache:
        def __init__(self, client):
            self.client = client
        async def get(self, prompt):
            return cached_response
        async def set(self, prompt, response):
            pass

    monkeypatch.setattr(chat_service, "SemanticCache", FakeSemanticCache)

    db = _MockDBSession()
    fake_redis = object()

    chunks = asyncio.run(_collect_stream(chat_service.generate_chat_stream(
        db, "user-100", "session-200", "RAG là gì?", redis_client=fake_redis
    )))

    # Kiểm tra DB lưu đủ cả câu hỏi của user và câu trả lời cache của assistant
    assert len(db.added_items) == 2
    user_msg, assistant_msg = db.added_items

    assert user_msg.role == "user"
    assert user_msg.content == "RAG là gì?"

    assert user_msg.user_id == "user-100"
    assert user_msg.session_id == "session-200"

    assert assistant_msg.role == "assistant"
    assert assistant_msg.content == "Đây là câu trả lời được lấy từ cache, rất nhanh chóng và chính xác."
    assert assistant_msg.agent_type == "cache"
    assert assistant_msg.metadata_json == cached_response
    assert db.committed is True

    # Kiểm tra SSE events được bắn ra đúng
    payloads = [json.loads(c[6:]) for c in chunks if c.startswith("data: ") and c != "data: [DONE]\n\n"]
    assert any(p.get("type") == "status" for p in payloads)
    assert any(p.get("type") == "token" for p in payloads)
    assert payloads[-1]["type"] == "metadata"
    assert payloads[-1]["response"]["text"] == "Đây là câu trả lời được lấy từ cache, rất nhanh chóng và chính xác."
    assert chunks[-1] == "data: [DONE]\n\n"

def test_semantic_cache_openai_embedding_records_usage_without_content(monkeypatch):
    recorded = {}

    class Observation:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def update(self, **kwargs):
            assert "input" not in kwargs
            assert "output" not in kwargs
            recorded["usage"] = kwargs["usage_details"]

    class Client:
        def start_as_current_observation(self, **kwargs):
            recorded["model"] = kwargs["model"]
            return Observation()

    class EmbeddingsClient:
        def create(self, *, input, model):
            assert input == ["private prompt"]
            assert model == "text-embedding-3-small"
            return SimpleNamespace(
                data=[SimpleNamespace(embedding=[0.1, 0.2, 0.3])],
                usage=SimpleNamespace(prompt_tokens=7, total_tokens=7),
            )

    class Embeddings:
        client = EmbeddingsClient()

    monkeypatch.setattr(
        semantic_cache_module,
        "get_langfuse_client",
        lambda: Client(),
    )
    cache = SemanticCache.__new__(SemanticCache)
    cache.model_name = "text-embedding-3-small"
    cache.embeddings = Embeddings()
    cache._uses_openai_embeddings = True

    vector = cache._embed("private prompt")

    assert vector.tolist() == pytest.approx([0.1, 0.2, 0.3])
    assert recorded["usage"] == {"input": 7, "total": 7}
    assert recorded["model"] == "text-embedding-3-small"


def test_semantic_cache_decision_logic():
    """Kiểm thử logic ra quyết định của Semantic Cache (chuẩn hóa, chất lượng, intent, threshold)."""
    # 1. Chuẩn hóa prompt
    assert normalize_query("  RAG   là gì? ") == "rag là gì?"

    # 2. Quy tắc kiểm tra cache lookup
    assert not is_cache_lookup_allowed("rag").allowed  # Quá ngắn
    assert not is_cache_lookup_allowed("viết code: ```python\nprint()```").allowed  # Chứa code block
    assert not is_cache_lookup_allowed("giải thích thêm câu trên").allowed  # Phụ thuộc lịch sử
    assert is_cache_lookup_allowed("RAG là gì và hoạt động thế nào?").allowed  # Hợp lệ

    # 3. Quy tắc kiểm tra chất lượng response cacheable
    assert not is_response_cacheable("RAG là gì?", {"text": "Lỗi hệ thống", "type": "error"})
    assert not is_response_cacheable("RAG là gì?", {"text": "Xin lỗi, tôi không tìm thấy thông tin bài giảng.", "type": "rag"})  # Nghi ngờ chất lượng thấp
    assert is_response_cacheable("RAG là gì?", {"text": "RAG là viết tắt của Retrieval-Augmented Generation, là một kỹ thuật...", "type": "rag"})

    # 4. Kiểm tra trùng khớp Intent
    assert same_intent("RAG là gì?", "Định nghĩa RAG?")
    assert not same_intent("So sánh RAG và Fine-tuning", "RAG là gì?")  # Intent So sánh vs Định nghĩa khác nhau

    # 5. Đánh giá Candidate tương tự
    candidate = {
        "quality_status": "ok",
        "cacheable": True,
        "cache_scope": "global",
        "response_text": "RAG là viết tắt của Retrieval-Augmented Generation...",
        "response_json": {"text": "RAG là viết tắt của Retrieval-Augmented Generation..."},
        "prompt": "RAG là gì?",
        "similarity": 0.95,
    }

    # Similarity cao vượt threshold -> Hit
    decision = should_use_candidate("Giải thích cho tôi RAG là gì?", candidate)
    assert decision.hit is True
    assert decision.reason == "strong_semantic_hit"

    # Similarity thấp dưới threshold -> Miss
    low_sim_candidate = dict(candidate, similarity=0.80)
    decision = should_use_candidate("Giải thích cho tôi RAG là gì?", low_sim_candidate)
    assert decision.hit is False
    assert decision.reason == "below_vector_threshold"


def test_chat_stream_low_quality_response_not_cached(monkeypatch):
    """Kiểm thử response lỗi/nghi ngờ không được cache vào Redis."""
    monkeypatch.setattr(chat_service, "SEMANTIC_CACHE_ENABLED", True)

    set_called = False
    class TrackingSemanticCache:
        def __init__(self, client):
            self.client = client
        async def get(self, prompt):
            return None
        async def set(self, prompt, response):
            nonlocal set_called
            set_called = True

    monkeypatch.setattr(chat_service, "SemanticCache", TrackingSemanticCache)

    # Mock workflow trả về câu trả lời quá ngắn (không đạt chất lượng)
    class LowQualityWorkflow:
        async def astream_events(self, *_args, **_kwargs):
            yield {
                "event": "on_chain_end",
                "metadata": {"langgraph_node": "tutor"},
                "data": {
                    "output": {
                        "response": {
                            "text": "Ngắn.",  # Quá ngắn (< 40 kí tự)
                            "type": "rag",
                        }
                    }
                },
            }

    monkeypatch.setattr(chat_service, "workflow", LowQualityWorkflow(), raising=False)

    db = _MockDBSession()
    fake_redis = object()

    # Chạy stream
    asyncio.run(_collect_stream(chat_service.generate_chat_stream(
        db, "user-100", "session-200", "RAG là gì?", redis_client=fake_redis
    )))

    # Vẫn lưu DB bình thường
    assert len(db.added_items) == 2
    # Nhưng gọi cache provider set (nơi bộ lọc bên trong sẽ ngăn không cho lưu vào Redis)
    assert set_called is True

    # Kiểm tra trực tiếp lớp SemanticCache với client Redis giả để chắc chắn nó không ghi xuống Redis
    redis_hset_called = False
    class FakeRedisClient:
        def hset(self, *args, **kwargs):
            nonlocal redis_hset_called
            redis_hset_called = True
        def get(self, *args, **kwargs):
            return None
        def ft(self, *args, **kwargs):
            class FakeFt:
                def info(self):
                    pass
            return FakeFt()

    cache = SemanticCache(FakeRedisClient())
    # Lưu câu ngắn -> Không ghi
    cache.set_sync("RAG là gì?", {"text": "Ngắn.", "type": "rag"})
    assert redis_hset_called is False

    # Lưu câu tốt -> Ghi thành công
    # Mock embed để trả về numpy array thích hợp
    monkeypatch.setattr(cache, "_embed", lambda p: np.zeros(1536, dtype=np.float32))
    cache.set_sync("Giải thích RAG chi tiết?", {
        "text": "RAG là viết tắt của Retrieval-Augmented Generation, một giải pháp kết hợp tìm kiếm ngữ cảnh ngoài để trả lời.",
        "type": "rag"
    })
    assert redis_hset_called is True


def test_cancelled_stream_closes_request_without_done(monkeypatch):
    class CancelledWorkflow:
        async def astream_events(self, *_args, **_kwargs):
            yield {
                "event": "on_chain_start",
                "metadata": {"langgraph_node": "supervisor"},
            }
            raise asyncio.CancelledError()

    monkeypatch.setattr(chat_service, "workflow", CancelledWorkflow())
    monkeypatch.setattr(chat_service, "SEMANTIC_CACHE_ENABLED", False)
    labels = {"route": "unknown", "outcome": "cancelled", "cache": "disabled"}
    before = REGISTRY.get_sample_value("puq_chat_requests_total", labels) or 0
    active_before = REGISTRY.get_sample_value("puq_chat_active") or 0
    chunks = []

    async def consume():
        async for chunk in chat_service.generate_chat_stream(
            _MockDBSession(), "user-1", "conv-1", "Hãy giải thích CNN"
        ):
            chunks.append(chunk)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(consume())

    assert any('"type": "status"' in chunk for chunk in chunks)
    assert "data: [DONE]\n\n" not in chunks
    assert (REGISTRY.get_sample_value("puq_chat_requests_total", labels) or 0) == before + 1
    assert (REGISTRY.get_sample_value("puq_chat_active") or 0) == active_before


def test_status_only_stream_does_not_record_first_answer_token(monkeypatch):
    class StatusOnlyWorkflow:
        async def astream_events(self, *_args, **_kwargs):
            yield {
                "event": "on_chain_start",
                "metadata": {"langgraph_node": "supervisor"},
            }
            yield {
                "event": "on_chain_end",
                "metadata": {"langgraph_node": "direct"},
                "data": {"output": {"response": {
                    "text": "Xin chào", "type": "direct", "video_url": [],
                    "title": [], "filename": [], "start_timestamp": [],
                    "end_timestamp": [], "confidence": [],
                }}},
            }

    monkeypatch.setattr(chat_service, "workflow", StatusOnlyWorkflow())
    monkeypatch.setattr(chat_service, "SEMANTIC_CACHE_ENABLED", False)
    labels = {"route": "direct", "cache": "disabled"}
    before = REGISTRY.get_sample_value("puq_chat_ttft_seconds_count", labels) or 0

    chunks = asyncio.run(_collect_stream(chat_service.generate_chat_stream(
        _MockDBSession(), "user-1", "conv-1", "Xin chào"
    )))

    assert chunks[-1] == "data: [DONE]\n\n"
    assert not any('"type": "token"' in chunk for chunk in chunks)
    assert (REGISTRY.get_sample_value("puq_chat_ttft_seconds_count", labels) or 0) == before


def test_metadata_only_trace_uses_stable_opaque_session_id(monkeypatch):
    from langfuse import Langfuse
    from langfuse.langchain import CallbackHandler
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from src.shared.observability import mask_otel_spans

    monkeypatch.setenv("PUQ_TRACE_CONTENT", "false")
    monkeypatch.setenv("LANGFUSE_TRACING_ENABLED", "true")
    monkeypatch.setattr(chat_service, "SEMANTIC_CACHE_ENABLED", False)
    monkeypatch.setattr(chat_service, "workflow", _SingleRunWorkflow())
    public_key = f"pk-{uuid.uuid4().hex}"
    exporter = InMemorySpanExporter()
    client = Langfuse(
        public_key=public_key,
        secret_key="sk-test",
        base_url="http://langfuse.test",
        tracer_provider=TracerProvider(),
        span_exporter=exporter,
        mask_otel_spans=mask_otel_spans,
        flush_at=1,
    )
    monkeypatch.setattr(chat_service, "get_langfuse_client", lambda: client)
    monkeypatch.setattr(chat_service, "CallbackHandler", lambda: CallbackHandler(public_key=public_key))

    try:
        for user in ("user-one", "user-one", "user-two"):
            asyncio.run(_collect_stream(chat_service.generate_chat_stream(
                _MockDBSession(), user, "secretAccount123", "Xin chào"
            )))
        client.flush()
        roots = [span for span in exporter.get_finished_spans() if span.name == "chat_stream"]
        assert len(roots) == 3
        session_ids = [span.attributes["session.id"] for span in roots]
        assert session_ids[0] == session_ids[1]
        assert session_ids[0] != session_ids[2]
        assert all(len(session_id) == 64 for session_id in session_ids)
        assert "secretAccount123" not in repr([dict(span.attributes) for span in roots])
    finally:
        client.shutdown()
