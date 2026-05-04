"""
Service xử lý hội thoại (Chat) với AI Engine.
Hỗ trợ Streaming SSE, Semantic Caching, và lưu trữ lịch sử vào DB.
"""

import asyncio
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

from src.rag_core.lang_graph_rag import workflow
from backend.app.models.user import ChatHistory
from backend.app.schemas.chat import ChatRequest, ChatResponse
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


async def _yield_token_events(token: str) -> AsyncGenerator[str, None]:
    """Yield SSE token events theo mảnh nhỏ để tránh browser nhận một cục lớn."""
    for chunk in _split_stream_token(token):
        yield f"data: {json_lib.dumps({'type': 'token', 'content': chunk})}\n\n"
        await asyncio.sleep(0)


# --- Core Service Logic ---


async def generate_chat_stream(
    db: Session,
    user_id: Any,
    session_id: str,
    user_message: str,
    redis_client: Optional[redis.Redis] = None,
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
        cache_provider = SemanticCache(redis_client)
        cached_resp = await cache_provider.get(user_message)
        if cached_resp:
            yield f"data: {json_lib.dumps({'type': 'status', 'status': '✨ Đang tổng hợp câu trả lời phù hợp...'})}\n\n"

            full_text = cached_resp.get("text", "")
            await asyncio.sleep(0.12)
            for chunk in _split_stream_token(full_text, max_chars=18):
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
        async for event in workflow.astream_events(initial_state, version="v2"):
            node_name = event.get("metadata", {}).get("langgraph_node", "")
            event_type = event.get("event")

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

                token_text = _extract_stream_token_content(
                    event.get("data", {}).get("chunk")
                )
                if token_text:
                    if "final_answer_json" not in tags and _looks_like_json_fragment(token_text):
                        continue
                    clean_token = cleaner.process_token(token_text)
                    if clean_token:
                        async for token_event in _yield_token_events(clean_token):
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

        # Lưu phản hồi Assistant vào DB
        if final_response and isinstance(final_response, dict):
            assistant_chat = ChatHistory(
                user_id=user_id,
                session_id=session_id,
                role="assistant",
                content=final_response.get("text", ""),
                agent_type=node_name,
                metadata_json=final_response,
            )
            db.add(assistant_chat)
            db.commit()

            # 5. Lưu vào Semantic Cache (Nếu thành công)
            if cache_provider and final_response.get("text"):
                await cache_provider.set(user_message, final_response)

        yield f"data: {json_lib.dumps({'type': 'metadata', 'conversation_id': session_id, 'response': final_response})}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as e:
        logger.error(f"Chat stream error: {e}")
        yield f"data: {json_lib.dumps({'type': 'error', 'content': str(e)})}\n\n"
        yield "data: [DONE]\n\n"


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
