"""
Service xử lý hội thoại (Chat) với AI Engine.
Hỗ trợ Streaming SSE, Semantic Caching, và lưu trữ lịch sử vào DB.
"""
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
        self.last_yielded_len = 0
        self.target_keys = ['"text"', '"goal"', '"content"']
        self.capture_start_idx = -1

    def process_token(self, token: str) -> str:
        if self.is_plain_text:
            return token
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

            extracted_raw = self.buffer[self.capture_start_idx:]
            end_quote_idx = -1
            for i in range(len(extracted_raw)):
                if extracted_raw[i] == '"' and (i == 0 or extracted_raw[i-1] != '\\'):
                    end_quote_idx = i
                    break
            
            content_to_decode = extracted_raw if end_quote_idx == -1 else extracted_raw[:end_quote_idx]
            try:
                if content_to_decode.endswith('\\'):
                    content_to_decode = content_to_decode[:-1]
                decoded = json_lib.loads(f'"{content_to_decode}"')
                delta = decoded[self.last_yielded_len:]
                self.last_yielded_len = len(decoded)
                return delta
            except:
                return ""
        return token

# --- Helper functions ---

def _extract_stream_token_content(chunk: Any) -> str:
    """Trích xuất nội dung text từ chunk của LangChain stream."""
    if chunk is None: return ""
    if isinstance(chunk, str): return chunk
    content = getattr(chunk, "content", None)
    if isinstance(content, str): return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str): parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str): parts.append(text)
        return "".join(parts)
    if isinstance(chunk, dict):
        dict_content = chunk.get("content")
        if isinstance(dict_content, str): return dict_content
    return ""

def _extract_stream_context(event: dict) -> list:
    """Trích xuất danh sách video (context) từ event data."""
    data = event.get("data", {})
    output = data.get("output")
    if not output: return []
    if isinstance(output, str) and output.startswith("["):
        try: return json_lib.loads(output)
        except: return []
    return []

# --- Core Service Logic ---

async def generate_chat_stream(
    db: Session,
    user_id: Any,
    session_id: str,
    user_message: str,
    redis_client: Optional[redis.Redis] = None
) -> AsyncGenerator[str, None]:
    """
    Generator xử lý hội thoại AI:
    1. Kiểm tra Semantic Cache (Redis).
    2. Gọi LangGraph workflow.
    3. Stream từng token về client.
    4. Lưu kết quả vào PostgreSQL.
    """
    # 1. Kiểm tra Semantic Cache (Nếu bật)
    cache_provider = None
    if SEMANTIC_CACHE_ENABLED and redis_client:
        cache_provider = SemanticCache(redis_client)
        cached_resp = await cache_provider.get(user_message)
        if cached_resp:
            # Nếu là cache hit, stream kết quả ngay lập tức
            yield f"data: {json_lib.dumps({'type': 'status', 'status': '🚀 Phản hồi nhanh từ bộ nhớ đệm...'})}\n\n"
            
            # Giả lập streaming cho UX tốt hơn
            full_text = cached_resp.get("text", "")
            words = full_text.split(" ")
            for i in range(0, len(words), 5):
                chunk = " ".join(words[i:i+5]) + " "
                yield f"data: {json_lib.dumps({'type': 'token', 'content': chunk})}\n\n"
                time.sleep(0.02)
            
            yield f"data: {json_lib.dumps({'type': 'metadata', 'conversation_id': session_id, 'response': cached_resp})}\n\n"
            yield "data: [DONE]\n\n"
            
            # Vẫn lưu vào lịch sử DB
            assistant_chat = ChatHistory(
                user_id=user_id,
                session_id=session_id,
                role="assistant",
                content=full_text,
                agent_type="cache",
                metadata_json=cached_resp
            )
            db.add(assistant_chat)
            db.commit()
            return

    # 2. Lấy lịch sử hội thoại từ DB
    history = db.query(ChatHistory).filter(
        ChatHistory.user_id == user_id,
        ChatHistory.session_id == session_id
    ).order_by(ChatHistory.created_at.asc()).all()
    
    # Giới hạn lịch sử
    history = history[-MAX_HISTORY_MESSAGES:]
    
    # Build LangChain messages
    langchain_messages = []
    for msg in history:
        if msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content))
        else:
            langchain_messages.append(AIMessage(content=msg.content))
    
    # Thêm tin nhắn mới của user
    langchain_messages.append(HumanMessage(content=user_message))
    
    # Lưu tin nhắn User vào DB ngay lập tức
    user_chat = ChatHistory(
        user_id=user_id,
        session_id=session_id,
        role="user",
        content=user_message
    )
    db.add(user_chat)
    db.commit()

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

    final_response = {
        "text": "",
        "type": "error",
        "metadata": {}
    }
    
    try:
        async for event in workflow.astream_events(initial_state, version="v2"):
            node_name = event.get("metadata", {}).get("langgraph_node", "")
            event_type = event.get("event")

            # Stream Status
            if event_type == "on_chain_start" and node_name in STATUS_MAPPING:
                yield f"data: {json_lib.dumps({'type': 'status', 'status': STATUS_MAPPING[node_name]})}\n\n"

            # Stream Context (Citations)
            if event_type == "on_chain_end":
                context_docs = _extract_stream_context(event)
                if context_docs:
                    yield f"data: {json_lib.dumps({'type': 'context', 'docs': context_docs})}\n\n"

            # Stream Tokens
            if event_type == "on_chat_model_stream":
                if node_name in ["supervisor", "agent", "gen_sympy", "verify"]:
                    continue
                
                token_text = _extract_stream_token_content(event.get("data", {}).get("chunk"))
                if token_text:
                    clean_token = cleaner.process_token(token_text)
                    if clean_token:
                        yield f"data: {json_lib.dumps({'type': 'token', 'content': clean_token})}\n\n"
            
            # Capture Final Output of the winning node
            if event_type == "on_chain_end" and node_name in ["tutor", "math", "quiz", "coding", "direct"]:
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
                metadata_json=final_response
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


def get_chat_history(db: Session, user_id: Any, session_id: Optional[str] = None, limit: int = 50) -> List[ChatHistory]:
    """Lấy lịch sử hội thoại của user. Nếu có session_id thì chỉ lấy của session đó."""
    query = db.query(ChatHistory).filter(ChatHistory.user_id == user_id)
    if session_id:
        query = query.filter(ChatHistory.session_id == session_id)
    return query.order_by(ChatHistory.created_at.asc()).limit(limit).all()


def get_chat_sessions(db: Session, user_id: Any, limit: int = 20) -> List[Dict[str, Any]]:
    """Lấy danh sách các phiên hội thoại (session_id) duy nhất của user."""
    from sqlalchemy import func
    
    # Lấy tin nhắn đầu tiên của mỗi session để làm tiêu đề
    subquery = db.query(
        ChatHistory.session_id,
        func.min(ChatHistory.created_at).label("first_msg_time")
    ).filter(ChatHistory.user_id == user_id).group_by(ChatHistory.session_id).subquery()
    
    sessions = db.query(ChatHistory).join(
        subquery,
        (ChatHistory.session_id == subquery.c.session_id) & 
        (ChatHistory.created_at == subquery.c.first_msg_time)
    ).order_by(subquery.c.first_msg_time.desc()).limit(limit).all()
    
    return [
        {
            "session_id": s.session_id,
            "title": s.content[:50] + "..." if len(s.content) > 50 else s.content,
            "created_at": s.created_at
        }
        for s in sessions
    ]
