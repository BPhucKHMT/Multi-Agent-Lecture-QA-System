"""
Service xử lý hội thoại (Chat) với AI Engine.
Hỗ trợ Streaming SSE, Semantic Caching, và lưu trữ lịch sử vào DB.
"""

import asyncio
import hashlib
import hmac
from collections.abc import Callable
from contextlib import aclosing, nullcontext
from dataclasses import dataclass, field
import json as json_lib
import logging
import os
import re
import time
import uuid
import unicodedata
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy.orm import Session
import redis
from langchain_core.messages import HumanMessage, AIMessage
from langfuse import propagate_attributes
from langfuse.langchain import CallbackHandler

from src.rag_core.lang_graph_rag import workflow
from src.shared.metrics import CHAT_ACTIVE, CHAT_DURATION, CHAT_REQUESTS, CHAT_TTFT
from src.shared.observability import get_langfuse_client, trace_content_enabled
from backend.app.models.user import ChatHistory
from backend.app.core.config import settings
from backend.app.core.cache.semantic import SemanticCache

SEMANTIC_CACHE_ENABLED = settings.SEMANTIC_CACHE_ENABLED

logger = logging.getLogger(__name__)

# --- Cấu hình ---
MAX_HISTORY_MESSAGES = int(os.getenv("PUQ_MAX_STREAM_HISTORY_MESSAGES", "8"))

# --- Hỗ trợ xử lý JSON Stream ---


class JsonStreamCleaner:
    """Hỗ trợ bóc tách nội dung text sạch từ một luồng JSON dở dang của LLM."""

    def __init__(self):
        self.buffer = ""
        self.is_json = False
        self.is_plain_text = False
        self.target_keys = ['"text"', '"goal"', '"content"']
        self.capture_start_idx = -1
        self.raw_cursor = 0
        self.pending_escape = ""
        self.capture_done = False

    def process_token(self, token: str) -> str:
        if self.is_plain_text:
            return token
        if self.capture_done:
            return ""
        self.buffer += token

        if not self.is_json:
            stripped = self.buffer.lstrip()
            if stripped.startswith("{"):
                self.is_json = True
            elif stripped.startswith("```"):
                start_idx = self.buffer.find("{")
                if start_idx != -1:
                    self.buffer = self.buffer[start_idx:]
                    self.is_json = True
                elif len(stripped) < 15:
                    return ""
                else:
                    self.is_plain_text = True
                    return self.buffer
            elif stripped:
                self.is_plain_text = True
                return self.buffer
            else:
                return ""

        if self.is_json:
            if self.capture_start_idx == -1:
                for key in self.target_keys:
                    key_idx = self.buffer.find(key)
                    if key_idx != -1:
                        colon_idx = self.buffer.find(":", key_idx + len(key))
                        if colon_idx != -1:
                            quote_idx = self.buffer.find('"', colon_idx + 1)
                            if quote_idx != -1:
                                self.capture_start_idx = quote_idx + 1
                                break
                if self.capture_start_idx == -1:
                    return ""

            extracted_raw = self.buffer[self.capture_start_idx :]
            return self._decode_text_delta(extracted_raw)
        return token

    def _decode_text_delta(self, extracted_raw: str) -> str:
        """Giải mã từng phần value JSON string mà không chờ object hoàn chỉnh."""
        out = []
        i = self.raw_cursor

        while i < len(extracted_raw):
            char = extracted_raw[i]

            if self.pending_escape:
                self.pending_escape += char
                if self.pending_escape.startswith("\\u"):
                    if len(self.pending_escape) < 6:
                        i += 1
                        continue
                    try:
                        out.append(chr(int(self.pending_escape[2:6], 16)))
                    except ValueError:
                        out.append(self.pending_escape)
                    self.pending_escape = ""
                    i += 1
                    continue

                escape_char = self.pending_escape[1]
                escape_map = {
                    '"': '"',
                    "\\": "\\",
                    "/": "/",
                    "b": "\b",
                    "f": "\f",
                    "n": "\n",
                    "r": "\r",
                    "t": "\t",
                }
                out.append(escape_map.get(escape_char, self.pending_escape))
                self.pending_escape = ""
                i += 1
                continue

            if char == "\\":
                self.pending_escape = "\\"
                i += 1
                continue
            if char == '"':
                self.capture_done = True
                i += 1
                break

            out.append(char)
            i += 1

        self.raw_cursor = i
        return "".join(out)


# --- Helper functions ---


def _extract_stream_token_content(chunk: Any) -> str:
    """Trích xuất nội dung text từ chunk của LangChain stream."""
    if chunk is None:
        return ""
    if isinstance(chunk, str):
        return chunk
    content = getattr(chunk, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    if isinstance(chunk, dict):
        dict_content = chunk.get("content")
        if isinstance(dict_content, str):
            return dict_content
    return ""


def _extract_stream_context(event: dict) -> list:
    """Trích xuất danh sách video (context) từ event data."""
    data = event.get("data", {})
    output = data.get("output")
    if not output:
        return []
    if isinstance(output, str) and output.startswith("["):
        try:
            parsed = json_lib.loads(output)
            if (
                isinstance(parsed, list)
                and len(parsed) > 0
                and isinstance(parsed[0], dict)
                and ("page_content" in parsed[0] or "content" in parsed[0])
            ):
                return parsed
            return []
        except Exception:
            return []
    return []


def _looks_like_json_fragment(token: str) -> bool:
    """Phát hiện token là mảnh JSON/metadata để không stream ra UI."""
    stripped = (token or "").strip()
    if not stripped:
        return True

    # Structural token hoặc key/value metadata thường gặp
    if stripped in {"{", "}", "[", "]", ",", ":", '"'}:
        return True
    if all(c in '{}[],:"\n\t ' for c in stripped):
        return True
    if re.search(
        r'"(text|video_url|title|filename|start_timestamp|end_timestamp|confidence|type|quizzes|math_data|goal|steps)"\s*:',
        stripped,
    ):
        return True

    return False


def _split_stream_token(token: str, max_chars: int = 24) -> List[str]:
    """Chia token lớn thành các mảnh nhỏ để UI render mượt hơn."""
    if len(token) <= max_chars:
        return [token]

    chunks = []
    current = ""
    for part in re.split(r"(\s+)", token):
        if len(current) + len(part) > max_chars and current:
            chunks.append(current)
            current = part
        else:
            current += part

    if current:
        chunks.append(current)
    return chunks


async def _yield_token_events(
    token: str, on_first_visible: Callable[[], None] | None = None
) -> AsyncGenerator[str, None]:
    """Yield SSE token events theo mảnh nhỏ để tránh browser nhận một cục lớn."""
    for chunk in _split_stream_token(token):
        if on_first_visible is not None and chunk.strip():
            on_first_visible()
            on_first_visible = None
        yield f"data: {json_lib.dumps({'type': 'token', 'content': chunk})}\n\n"
        await asyncio.sleep(0)


# --- Core Service Logic ---
@dataclass(slots=True)
class _StreamTelemetry:
    started: float = field(default_factory=time.perf_counter)
    route: str = "unknown"
    cache: str = "disabled"
    outcome: str = "error"
    response_type: str = "error"
    answer_chars: int = 0
    citation_count: int = 0
    first_token_recorded: bool = False
    response: dict | None = None

    def mark_first_visible(self) -> None:
        if self.first_token_recorded:
            return
        self.first_token_recorded = True
        CHAT_TTFT.labels(route=self.route, cache=self.cache).observe(
            time.perf_counter() - self.started
        )

    def complete(self, response: dict) -> None:
        self.response = response
        response_type = response.get("type", "error")
        self.response_type = (
            response_type
            if response_type in {"rag", "quiz", "math", "coding", "direct", "error"}
            else "error"
        )
        text = response.get("text")
        citations = response.get("video_url")
        self.answer_chars = len(text) if isinstance(text, str) else 0
        self.citation_count = len(citations) if isinstance(citations, list) else 0
        self.outcome = "error" if self.response_type == "error" else "success"




async def _generate_chat_stream(
    db: Session,
    user_id: Any,
    session_id: str,
    user_message: str,
    redis_client: Optional[redis.Redis],
    telemetry: _StreamTelemetry,
    callbacks: list,
) -> AsyncGenerator[str, None]:
    """
    Generator xử lý hội thoại AI:
    1. Kiểm tra Semantic Cache (Redis).
    2. Gọi LangGraph workflow.
    3. Stream từng token về client.
    4. Lưu kết quả vào PostgreSQL.
    """
    # 1. Lấy lịch sử hội thoại từ DB trước khi thêm message mới
    history = (
        db.query(ChatHistory)
        .filter(ChatHistory.user_id == user_id, ChatHistory.session_id == session_id)
        .order_by(ChatHistory.created_at.asc())
        .all()
    )
    history = history[-MAX_HISTORY_MESSAGES:]

    langchain_messages = []
    for msg in history:
        if msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content))
        else:
            langchain_messages.append(AIMessage(content=msg.content))

    langchain_messages.append(HumanMessage(content=user_message))

    # 2. Lưu user message trước cache lookup để history không bị thiếu khi cache hit
    user_chat = ChatHistory(
        user_id=user_id, session_id=session_id, role="user", content=user_message
    )
    db.add(user_chat)
    db.commit()

    # 3. Kiểm tra Semantic Cache sau khi DB đã có câu hỏi user
    cache_provider = None
    if SEMANTIC_CACHE_ENABLED and redis_client:
        telemetry.cache = "miss"
        cache_provider = SemanticCache(redis_client)
        cached_resp = await cache_provider.get(user_message)
        if cached_resp:
            telemetry.cache = "hit"
            telemetry.route = "cache"
            yield f"data: {json_lib.dumps({'type': 'status', 'status': '✨ Đang tổng hợp câu trả lời phù hợp...'})}\n\n"

            full_text = cached_resp.get("text", "")
            await asyncio.sleep(0.12)
            for chunk in _split_stream_token(full_text, max_chars=18):
                if chunk.strip():
                    telemetry.mark_first_visible()
                yield f"data: {json_lib.dumps({'type': 'token', 'content': chunk})}\n\n"
                await asyncio.sleep(0.018 if chunk.strip() else 0.006)

            assistant_chat = ChatHistory(
                user_id=user_id,
                session_id=session_id,
                role="assistant",
                content=full_text,
                agent_type="cache",
                metadata_json=cached_resp,
            )
            db.add(assistant_chat)
            db.commit()
            telemetry.complete(cached_resp)

            yield f"data: {json_lib.dumps({'type': 'metadata', 'conversation_id': session_id, 'response': cached_resp})}\n\n"
            yield "data: [DONE]\n\n"
            return

    initial_state = {"messages": langchain_messages}
    cleaner = JsonStreamCleaner()

    STATUS_MAPPING = {
        "supervisor": "🤔 Đang phân tích yêu cầu của bạn...",
        "tutor": "📚 Đang truy hồi tri thức từ bài giảng...",
        "quiz": "📝 Đang soạn thảo câu hỏi trắc nghiệm...",
        "coding": "💻 Đang xử lý logic lập trình...",
        "math": "🔢 Đang thực hiện tính toán...",
        "direct": "💬 Đang chuẩn bị câu trả lời...",
    }

    final_response = {"text": "", "type": "error", "metadata": {}}

    try:
        async for event in workflow.astream_events(
            initial_state,
            version="v2",
            config={"callbacks": callbacks, "run_name": "puq-chat-workflow"},
        ):
            node_name = event.get("metadata", {}).get("langgraph_node", "")
            event_type = event.get("event")
            if event_type == "on_chain_start" and node_name in {
                "tutor", "quiz", "coding", "math", "direct"
            }:
                telemetry.route = node_name

            # Stream Status
            if event_type == "on_chain_start" and node_name in STATUS_MAPPING:
                yield f"data: {json_lib.dumps({'type': 'status', 'status': STATUS_MAPPING[node_name]})}\n\n"

            # Stream Context (Citations)
            if event_type == "on_chain_end" and event.get("name") == "retrieve_context":
                context_docs = _extract_stream_context(event)
                if context_docs:
                    yield f"data: {json_lib.dumps({'type': 'context', 'docs': context_docs})}\n\n"

            # Stream Tokens
            if event_type == "on_chat_model_stream":
                if node_name in ["supervisor", "agent", "gen_sympy", "verify"]:
                    continue

                tags = event.get("tags", [])
                # Chỉ stream token từ các LLM call được đánh dấu là câu trả lời cuối.
                # Các node nội bộ như coding.generate/fix/explain chỉ dùng để tạo dữ liệu trung gian,
                # nếu stream ra UI sẽ lộ code thô trước khi agent format response hoàn chỉnh.
                is_final_answer_stream = "final_answer" in tags or "final_answer_json" in tags
                if not is_final_answer_stream or "internal_query" in tags:
                    continue
                if node_name in {"tutor", "quiz", "coding", "math", "direct"}:
                    telemetry.route = node_name

                token_text = _extract_stream_token_content(
                    event.get("data", {}).get("chunk")
                )
                if token_text:
                    if "final_answer_json" not in tags and _looks_like_json_fragment(token_text):
                        continue
                    clean_token = cleaner.process_token(token_text)
                    if clean_token:
                        async for token_event in _yield_token_events(
                            clean_token, telemetry.mark_first_visible
                        ):
                            yield token_event

            # Capture Final Output of the winning node
            if event_type == "on_chain_end" and node_name in [
                "tutor",
                "math",
                "quiz",
                "coding",
                "direct",
            ]:
                output = event.get("data", {}).get("output")
                if isinstance(output, dict) and "response" in output:
                    final_response = output.get("response")
                    telemetry.route = node_name

        # Fallback nếu câu trả lời trống hoặc chỉ có khoảng trắng
        if not final_response or not isinstance(final_response, dict) or not final_response.get("text", "").strip():
            final_response = {
                "text": "Không nhận được phản hồi từ AI. Vui lòng thử lại.",
                "type": "error",
                "metadata": {}
            }

        # Lưu phản hồi Assistant vào DB
        if final_response and isinstance(final_response, dict):
            # Chỉ lưu các câu trả lời thực tế (không lưu lỗi kỹ thuật phát sinh từ luồng)
            if final_response.get("type") != "error" or final_response.get("text") == "Không nhận được phản hồi từ AI. Vui lòng thử lại.":
                assistant_chat = ChatHistory(
                    user_id=user_id,
                    session_id=session_id,
                    role="assistant",
                    content=final_response.get("text", ""),
                    agent_type=telemetry.route if final_response.get("type") != "error" else "error",
                    metadata_json=final_response,
                )
                db.add(assistant_chat)
                db.commit()

            # 5. Lưu vào Semantic Cache (Nếu thành công)
            if cache_provider and final_response.get("text"):
                await cache_provider.set(user_message, final_response)
        telemetry.complete(final_response)

        yield f"data: {json_lib.dumps({'type': 'metadata', 'conversation_id': session_id, 'response': final_response})}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as error:
        telemetry.outcome = "error"
        logger.error("Chat stream error (%s)", type(error).__name__)
        yield f"data: {json_lib.dumps({'type': 'error', 'content': 'Lỗi xử lý câu hỏi. Vui lòng thử lại.'})}\n\n"
        yield "data: [DONE]\n\n"


async def generate_chat_stream(
    db: Session,
    user_id: Any,
    session_id: str,
    user_message: str,
    redis_client: Optional[redis.Redis] = None,
) -> AsyncGenerator[str, None]:
    """Giữ một trace và bộ metrics cho đúng một lượt SSE, kể cả cache hit hoặc hủy."""
    telemetry = _StreamTelemetry()
    request_id = str(uuid.uuid4())
    CHAT_ACTIVE.inc()
    try:
        client = get_langfuse_client()
        callbacks = [CallbackHandler()] if client is not None else []
        observation = (
            client.start_as_current_observation(as_type="span", name="chat_stream")
            if client is not None else nullcontext()
        )
        with observation as root:
            if root is not None and trace_content_enabled():
                root.update(input={"text": user_message})
            if client is not None:
                trace_session_id = hmac.new(
                    settings.JWT_SECRET.encode("utf-8"),
                    f"{user_id}:{session_id}".encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest()
                attributes = propagate_attributes(
                    trace_name="puq-chat",
                    session_id=trace_session_id,
                    user_id=str(user_id),
                    metadata={"request_id": request_id},
                    tags=["chat"],
                )
            else:
                attributes = nullcontext()
            with attributes:
                try:
                    stream = _generate_chat_stream(
                        db, user_id, session_id, user_message, redis_client,
                        telemetry, callbacks,
                    )
                    async with aclosing(stream):
                        async for frame in stream:
                            yield frame
                except (asyncio.CancelledError, GeneratorExit):
                    telemetry.outcome = "cancelled"
                    raise
                except Exception:
                    telemetry.outcome = "error"
                    raise
                finally:
                    elapsed = time.perf_counter() - telemetry.started
                    CHAT_REQUESTS.labels(
                        route=telemetry.route,
                        outcome=telemetry.outcome,
                        cache=telemetry.cache,
                    ).inc()
                    CHAT_DURATION.labels(
                        route=telemetry.route,
                        outcome=telemetry.outcome,
                        cache=telemetry.cache,
                    ).observe(elapsed)
                    if root is not None:
                        root.update(metadata={
                            "route": telemetry.route,
                            "cache": telemetry.cache,
                            "outcome": telemetry.outcome,
                            "response_type": telemetry.response_type,
                            "answer_chars": telemetry.answer_chars,
                            "citation_count": telemetry.citation_count,
                        })
                        if trace_content_enabled() and telemetry.response is not None:
                            root.update(output={"text": telemetry.response.get("text", "")})
                    logger.info(
                        "chat_stream request_id=%s trace_id=%s route=%s cache=%s outcome=%s elapsed=%.3fs",
                        request_id, getattr(root, "trace_id", None), telemetry.route,
                        telemetry.cache, telemetry.outcome, elapsed,
                    )
    finally:
        CHAT_ACTIVE.dec()


def get_chat_history(
    db: Session, user_id: Any, session_id: Optional[str] = None, limit: int = 50
) -> List[ChatHistory]:
    """Lấy lịch sử hội thoại của user. Nếu có session_id thì chỉ lấy của session đó."""
    query = db.query(ChatHistory).filter(ChatHistory.user_id == user_id)
    if session_id:
        query = query.filter(ChatHistory.session_id == session_id)
    return query.order_by(ChatHistory.created_at.asc()).limit(limit).all()


def get_chat_sessions(
    db: Session, user_id: Any, limit: int = 20
) -> List[Dict[str, Any]]:
    """Lấy danh sách các phiên hội thoại (session_id) duy nhất của user."""
    from sqlalchemy import func

    # Lấy tin nhắn đầu tiên của mỗi session để làm tiêu đề
    subquery = (
        db.query(
            ChatHistory.session_id,
            func.min(ChatHistory.created_at).label("first_msg_time"),
        )
        .filter(ChatHistory.user_id == user_id)
        .group_by(ChatHistory.session_id)
        .subquery()
    )

    sessions = (
        db.query(ChatHistory)
        .join(
            subquery,
            (ChatHistory.session_id == subquery.c.session_id)
            & (ChatHistory.created_at == subquery.c.first_msg_time),
        )
        .order_by(subquery.c.first_msg_time.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "session_id": s.session_id,
            "title": s.content[:50] + "..." if len(s.content) > 50 else s.content,
            "created_at": s.created_at,
        }
        for s in sessions
    ]
