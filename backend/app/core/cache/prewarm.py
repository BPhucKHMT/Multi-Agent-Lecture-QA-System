"""Prewarm Redis semantic cache từ lịch sử chat trong DB."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Iterable

from sqlalchemy.orm import Session

from backend.app.core.cache.semantic import SemanticCache, is_response_cacheable
from backend.app.models.user import ChatHistory

logger = logging.getLogger(__name__)


def prewarm_semantic_cache(
    db: Session,
    cache: SemanticCache,
    limit: int,
) -> int:
    """Index N cặp user/assistant gần nhất vào Redis nếu đủ điều kiện cache."""
    cache.ensure_index()
    messages = (
        db.query(ChatHistory)
        .order_by(ChatHistory.created_at.desc())
        .limit(limit * 2)
        .all()
    )
    pairs = list(iter_chat_pairs(reversed(messages)))
    indexed = 0

    for question, answer in pairs[-limit:]:
        response = build_response(answer)
        if not is_response_cacheable(question.content, response):
            continue
        try:
            cache.set_sync(question.content, response)
            indexed += 1
        except Exception as exc:
            logger.warning("Skip semantic cache prewarm pair: %s", exc)

    return indexed


def iter_chat_pairs(messages: Iterable[ChatHistory]):
    """Ghép user message với assistant message ngay sau đó trong cùng session."""
    grouped = defaultdict(list)
    for message in messages:
        grouped[(message.user_id, message.session_id)].append(message)

    for group in grouped.values():
        previous_user = None
        for message in sorted(group, key=lambda item: item.created_at):
            if message.role == "user":
                previous_user = message
                continue
            if message.role == "assistant" and previous_user:
                yield previous_user, message
                previous_user = None


def build_response(answer: ChatHistory) -> dict:
    """Tạo response JSON từ assistant history để ghi lại vào Redis."""
    metadata = answer.metadata_json if isinstance(answer.metadata_json, dict) else {}
    response = dict(metadata)
    response.setdefault("text", answer.content)
    response.setdefault("type", answer.agent_type or metadata.get("type") or "rag")
    return response
