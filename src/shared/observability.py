"""Cấu hình Langfuse và hàng rào riêng tư cho telemetry.

Mặc định chỉ xuất metadata; khi bật PUQ_TRACE_CONTENT, chỉ root chat gửi
câu hỏi và câu trả lời lên Langfuse, không gửi nội dung các span con.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from typing import Any
from uuid import UUID

from langfuse import Langfuse
from langfuse.types import (
    MaskOtelSpansParams,
    MaskOtelSpansResult,
    OtelSpanPatch,
)


logger = logging.getLogger(__name__)


SAFE_ATTRIBUTES = frozenset(
    {
        "langfuse.observation.type",
        "langfuse.observation.level",
        "langfuse.observation.model.name",
        "langfuse.observation.usage_details",
        "langfuse.observation.cost_details",
        "langfuse.observation.completion_start_time",
        "langfuse.observation.metadata.model",
        "langfuse.observation.metadata.route",
        "langfuse.observation.metadata.response_type",
        "langfuse.observation.metadata.answer_chars",
        "langfuse.observation.metadata.citation_count",
        "langfuse.observation.metadata.cache",
        "langfuse.observation.metadata.outcome",
        "langfuse.trace.name",
        "langfuse.trace.tags",
        "langfuse.trace.metadata.request_id",
        "langfuse.environment",
        "langfuse.internal.as_root",
        "langfuse.internal.is_app_root",
        "user.id",
        "session.id",
    }
)

_TRACE_CONTENT_ATTRIBUTES = frozenset(
    {
        "langfuse.trace.output",
        "langfuse.observation.output",
        "langfuse.trace.input",
        "langfuse.observation.input",
    }
)
_ROOT_MARKER = "langfuse.internal.is_app_root"

_ALLOWED_ROUTES = frozenset(
    {"cache", "tutor", "quiz", "coding", "math", "direct", "unknown"}
)
_ALLOWED_CACHE = frozenset({"hit", "miss", "disabled"})
_ALLOWED_OUTCOMES = frozenset({"success", "error", "cancelled"})
_ALLOWED_RESPONSE_TYPES = frozenset({"rag", "quiz", "math", "coding", "direct", "error"})
_COUNT_FIELDS = frozenset({"answer_chars", "citation_count"})

# Chỉ che credential/token theo tên trường hoặc dạng Bearer. Regex này không
# phát hiện PII tự do; không được xem việc bật full output là chính sách PII.
_TOKEN_KEY_PATTERN = re.compile(
    r"""(?ix)(?P<prefix>['"]?(?:api[_-]?key|access[_-]?token|refresh[_-]?token|
    id[_-]?token|auth[_-]?token|secret(?:[_-]?key)?|password|authorization)
    ['"]?\s*[:=]\s*['"]?)(?P<value>[^\s,}\]'" ]+)(?P<quote>['"]?)"""
)
_BEARER_PATTERN = re.compile(r"(?i)(\bBearer\s+)[A-Za-z0-9._~+/=-]+")
_INTERNAL_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SAFE_TEXT_PATTERN = re.compile(r"^[^\x00-\x1f\x7f]{1,256}$")

_LANGFUSE_CLIENT: Any = None
_CLIENT_LOCK = threading.Lock()




def _is_enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() == "true"


def _credentials() -> tuple[str, str, str] | None:
    values = tuple(
        os.getenv(name, "").strip()
        for name in (
            "LANGFUSE_PUBLIC_KEY",
            "LANGFUSE_SECRET_KEY",
            "LANGFUSE_BASE_URL",
        )
    )
    return values if all(values) else None


def _is_configured() -> bool:
    return _is_enabled("LANGFUSE_TRACING_ENABLED") and _credentials() is not None




def trace_content_enabled() -> bool:
    """Cho biết input/output có được phép xuất ra Langfuse hay không."""
    return _is_enabled("PUQ_TRACE_CONTENT") and _is_configured()


def get_langfuse_client() -> Langfuse | None:
    """Trả singleton đã được khởi tạo; tuyệt đối không lazy-init SDK."""
    return _LANGFUSE_CLIENT


def initialize_langfuse() -> Langfuse | None:
    """Khởi tạo đúng một client Langfuse sau khi kiểm tra opt-in và đủ khóa."""
    global _LANGFUSE_CLIENT

    if _LANGFUSE_CLIENT is not None:
        return _LANGFUSE_CLIENT
    if not _is_configured():
        return None

    credentials = _credentials()
    if credentials is None:  # Bảo vệ thêm nếu env đổi giữa hai lần đọc.
        return None

    with _CLIENT_LOCK:
        if _LANGFUSE_CLIENT is not None:
            return _LANGFUSE_CLIENT
        try:
            public_key, secret_key, base_url = credentials
            _LANGFUSE_CLIENT = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                base_url=base_url.rstrip("/"),
                tracing_enabled=True,
                mask_otel_spans=mask_otel_spans,
            )
        except Exception:
            logger.exception("Không thể khởi tạo Langfuse; tiếp tục không có telemetry")
            return None

    return _LANGFUSE_CLIENT


def shutdown_langfuse() -> None:
    """Đóng client và xoá singleton SDK để lifespan có thể khởi động lại."""
    global _LANGFUSE_CLIENT

    with _CLIENT_LOCK:
        client = _LANGFUSE_CLIENT
        _LANGFUSE_CLIENT = None

    if client is None:
        return

    try:
        # SDK v4.15.6 chưa có public reset registry; dùng classmethod pinned
        # qua private module. reset() đóng và xoá mọi instance trong process,
        # phù hợp với contract ứng dụng chỉ sở hữu một singleton Langfuse.
        from langfuse._client.resource_manager import LangfuseResourceManager

        LangfuseResourceManager.reset()
    except Exception:
        try:
            client.shutdown()
        except Exception:
            logger.exception("Không thể đóng Langfuse client")


def _json_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value


def _safe_text(value: Any, *, max_length: int = 256) -> bool:
    return (
        isinstance(value, str)
        and len(value) <= max_length
        and bool(_SAFE_TEXT_PATTERN.fullmatch(value))
    )


def _safe_internal_id(value: Any) -> bool:
    return isinstance(value, str) and bool(_INTERNAL_ID_PATTERN.fullmatch(value))


def _safe_json_numbers(value: Any, *, allow_float: bool) -> bool:
    value = _json_value(value)
    if not isinstance(value, dict) or not value:
        return False
    for key, item in value.items():
        if not isinstance(key, str) or not _safe_text(key, max_length=64):
            return False
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            return False
        if not allow_float and not isinstance(item, int):
            return False
        if item < 0:
            return False
    return True


def _safe_attribute_value(key: str, value: Any) -> bool:
    """Kiểm tra value metadata ở ranh giới export, không chỉ tin tên key."""
    if key == "langfuse.observation.type":
        return value in {
            "span",
            "generation",
            "agent",
            "chain",
            "tool",
            "retriever",
            "embedding",
            "evaluator",
            "guardrail",
            "event",
        }
    if key == "langfuse.observation.level":
        return value in {"DEBUG", "DEFAULT", "WARNING", "ERROR"}
    if key == "langfuse.observation.model.name":
        return _safe_text(value, max_length=128)
    if key == "langfuse.observation.usage_details":
        return _safe_json_numbers(value, allow_float=False)
    if key == "langfuse.observation.cost_details":
        return _safe_json_numbers(value, allow_float=True)
    if key == "langfuse.observation.completion_start_time":
        return _safe_text(value, max_length=64)
    if key.startswith("langfuse.observation.metadata."):
        field = key.rsplit(".", 1)[-1]
        parsed = _json_value(value)
        if field in _COUNT_FIELDS:
            return (
                isinstance(parsed, int)
                and not isinstance(parsed, bool)
                and 0 <= parsed <= 10_000_000
            )
        if field == "model":
            return parsed == "jev-latest"
        if field == "route":
            return parsed in _ALLOWED_ROUTES
        if field == "cache":
            return parsed in _ALLOWED_CACHE
        if field == "outcome":
            return parsed in _ALLOWED_OUTCOMES
        if field == "response_type":
            return parsed in _ALLOWED_RESPONSE_TYPES
        return False
    if key == "langfuse.trace.name":
        return _safe_text(value, max_length=128)
    if key == "langfuse.trace.tags":
        parsed = _json_value(value)
        return isinstance(parsed, (list, tuple)) and all(
            _safe_text(item, max_length=64) for item in parsed
        )
    if key == "langfuse.trace.metadata.request_id":
        try:
            UUID(str(value))
        except (ValueError, TypeError, AttributeError):
            return False
        return True
    if key == "langfuse.environment":
        return _safe_text(value, max_length=64)
    if key in {"langfuse.internal.as_root", "langfuse.internal.is_app_root"}:
        return isinstance(value, bool)
    if key in {"user.id", "session.id"}:
        return _safe_internal_id(value)
    return False


def _mask_token_key_canaries(value: Any) -> Any:
    """Che credential/token theo key; không phải bộ lọc PII tổng quát."""
    if isinstance(value, str):
        value = _TOKEN_KEY_PATTERN.sub(
            lambda match: f"{match.group('prefix')}[REDACTED]{match.group('quote')}",
            value,
        )
        return _BEARER_PATTERN.sub(r"\1[REDACTED]", value)
    if isinstance(value, list):
        return [_mask_token_key_canaries(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_mask_token_key_canaries(item) for item in value)
    if isinstance(value, dict):
        return {
            key: "[REDACTED]"
            if isinstance(key, str)
            and re.search(
                r"(?i)(?:api[_-]?key|token|secret|password|authorization)", key
            )
            else _mask_token_key_canaries(item)
            for key, item in value.items()
        }
    return value


def mask_otel_spans(*, params: MaskOtelSpansParams) -> MaskOtelSpansResult:
    """Allowlist thuộc tính trước khi SDK gửi batch OTLP tới Langfuse."""
    patches: dict[Any, OtelSpanPatch] = {}
    capture_content = trace_content_enabled()

    for identifier, span in params.spans.items():
        attributes = getattr(span, "attributes", {}) or {}
        is_root = attributes.get(_ROOT_MARKER) is True
        delete_attributes: list[str] = []
        set_attributes: dict[str, Any] = {}

        for key, value in attributes.items():
            if not isinstance(key, str):
                continue
            keep = key in SAFE_ATTRIBUTES and _safe_attribute_value(key, value)
            if capture_content and is_root and key in _TRACE_CONTENT_ATTRIBUTES:
                keep = True
                set_attributes[key] = _mask_token_key_canaries(value)
            if not keep:
                delete_attributes.append(key)
        if delete_attributes or set_attributes:
            patches[identifier] = OtelSpanPatch(
                delete_attributes=tuple(delete_attributes),
                set_attributes=set_attributes,
            )

    return MaskOtelSpansResult(span_patches=patches)

__all__ = [
    "SAFE_ATTRIBUTES",
    "get_langfuse_client",
    "initialize_langfuse",
    "mask_otel_spans",
    "shutdown_langfuse",
    "trace_content_enabled",
]
