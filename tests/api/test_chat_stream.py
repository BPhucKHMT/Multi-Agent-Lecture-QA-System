import asyncio
import builtins
import json
import os
import sys
import hashlib
import uuid
import time
import numpy as np
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

from backend.app.services import chat as chat_service
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


class _BrokenWorkflow:
    async def astream_events(self, *_args, **_kwargs):
        raise RuntimeError("stream exploded")
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
    assert "stream exploded" in body["content"]
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
