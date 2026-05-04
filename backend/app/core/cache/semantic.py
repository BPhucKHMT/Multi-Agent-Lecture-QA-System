"""
Redis Stack semantic cache cho chat Q/A.

Cache này dùng exact SHA-256 trước, sau đó mới dùng vector search + guard
để hạn chế trả nhầm câu trả lời cho câu hỏi khác intent.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np
import redis
from langchain_openai import OpenAIEmbeddings
from redis.commands.search.field import NumericField, TagField, TextField, VectorField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

CONTEXT_DEPENDENT_PATTERNS = (
    "câu trên",
    "ở trên",
    "vừa nói",
    "tiếp tục",
    "giải thích thêm",
    "đoạn này",
    "code của tôi",
    "file này",
    "nội dung này",
)

GENERATIVE_PATTERNS = (
    "tạo quiz",
    "tạo câu hỏi",
    "ra đề",
    "cho ví dụ khác",
    "tạo mới",
)

LOW_QUALITY_PATTERNS = (
    "không chắc",
    "không tìm thấy",
    "không có thông tin",
    "xin lỗi",
    "i don't know",
)

VIETNAMESE_STOPWORDS = {
    "là",
    "gì",
    "của",
    "và",
    "thì",
    "mà",
    "có",
    "cho",
    "tôi",
    "bạn",
    "được",
    "không",
    "như",
    "nào",
    "hãy",
    "về",
    "một",
}

INTENT_MARKERS = {
    "definition": ("là gì", "định nghĩa", "giải thích"),
    "compare": ("so sánh", "khác gì", "khác nhau", "phân biệt"),
    "how": ("hoạt động", "như thế nào", "cách"),
    "why": ("tại sao", "vì sao"),
    "example": ("ví dụ", "minh họa"),
    "pros_cons": ("ưu điểm", "nhược điểm", "hạn chế"),
    "formula": ("công thức", "đạo hàm", "gradient"),
    "code": ("code", "python", "implement", "viết chương trình"),
}


@dataclass(frozen=True)
class CacheDecision:
    allowed: bool
    scope: str
    reason: str


@dataclass(frozen=True)
class CandidateDecision:
    hit: bool
    reason: str
    similarity: float = 0.0
    keyword_overlap: float = 0.0


class SemanticCache:
    """Semantic cache dùng Redis Stack vector search."""

    index_name = "idx:semantic_cache"
    item_prefix = "semantic_cache:item:"
    exact_prefix = "semantic_cache:exact:"

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.embeddings = OpenAIEmbeddings(
            model=settings.SEMANTIC_CACHE_EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )

    def ensure_index(self) -> None:
        """Tạo Redis Stack index nếu chưa tồn tại."""
        try:
            self.redis.ft(self.index_name).info()
            return
        except Exception:
            pass

        schema = (
            TextField("prompt"),
            TagField("quality_status"),
            TagField("cache_scope"),
            TagField("response_type"),
            NumericField("created_at"),
            VectorField(
                "embedding",
                "HNSW",
                {
                    "TYPE": "FLOAT32",
                    "DIM": settings.SEMANTIC_CACHE_VECTOR_DIM,
                    "DISTANCE_METRIC": "COSINE",
                },
            ),
        )
        definition = IndexDefinition(prefix=[self.item_prefix], index_type=IndexType.HASH)
        self.redis.ft(self.index_name).create_index(schema, definition=definition)

    async def get(self, prompt: str) -> Optional[dict[str, Any]]:
        """Tìm response cache theo exact key, sau đó dùng semantic vector search."""
        try:
            normalized = normalize_query(prompt)
            exact_hit = self._get_exact(normalized)
            if exact_hit:
                return exact_hit

            lookup_decision = is_cache_lookup_allowed(prompt)
            if not lookup_decision.allowed:
                return None

            query_vector = self._embed(prompt)
            candidates = self._search_candidates(query_vector)
            for candidate in candidates:
                decision = should_use_candidate(prompt, candidate)
                if decision.hit:
                    response = candidate["response_json"]
                    response.setdefault("metadata", {})
                    response["metadata"].update(
                        {
                            "cache_hit": True,
                            "cache_hit_type": "semantic_hybrid",
                            "cache_reason": decision.reason,
                            "similarity": decision.similarity,
                            "keyword_overlap": decision.keyword_overlap,
                            "cache_item_key": candidate["item_key"],
                        }
                    )
                    return response
            return None
        except Exception as exc:
            logger.warning("Semantic cache lookup failed: %s", exc)
            return None

    async def set(
        self,
        prompt: str,
        response: dict[str, Any],
        expire: Optional[int] = None,
    ) -> None:
        """Lưu Q/A cache nếu vượt quality/cacheability filter."""
        self.set_sync(prompt, response, expire)

    def set_sync(
        self,
        prompt: str,
        response: dict[str, Any],
        expire: Optional[int] = None,
    ) -> None:
        """Lưu Q/A cache bằng Redis sync client."""
        try:
            if not is_response_cacheable(prompt, response):
                return

            self.ensure_index()
            normalized = normalize_query(prompt)
            item_key = f"{self.item_prefix}{uuid.uuid4()}"
            exact_key = self._exact_key(normalized)
            response_json = json.dumps(response, ensure_ascii=False)
            vector = self._embed(prompt).tobytes()
            now = int(time.time())
            ttl = expire or settings.SEMANTIC_CACHE_TTL_SECONDS

            mapping = {
                "prompt": prompt,
                "normalized_prompt": normalized,
                "response_json": response_json,
                "response_text": response.get("text", ""),
                "response_type": response.get("type", "rag"),
                "cache_scope": "global",
                "cacheable": "true",
                "quality_status": "ok",
                "created_at": now,
                "embedding": vector,
            }
            self.redis.hset(item_key, mapping=mapping)
            self.redis.setex(exact_key, ttl, item_key)
            self.redis.expire(item_key, ttl)
        except Exception as exc:
            logger.warning("Semantic cache write failed: %s", exc)

    def _get_exact(self, normalized_prompt: str) -> Optional[dict[str, Any]]:
        item_key = self.redis.get(self._exact_key(normalized_prompt))
        if not item_key:
            return None
        if isinstance(item_key, bytes):
            item_key = item_key.decode("utf-8")

        payload = self.redis.hgetall(item_key)
        candidate = parse_candidate_payload(item_key, payload)
        if not candidate or not is_candidate_usable(candidate):
            return None

        response = candidate["response_json"]
        response.setdefault("metadata", {})
        response["metadata"].update(
            {
                "cache_hit": True,
                "cache_hit_type": "exact",
                "cache_reason": "exact_hash_hit",
                "cache_item_key": item_key,
            }
        )
        return response

    def _search_candidates(self, query_vector: np.ndarray) -> list[dict[str, Any]]:
        self.ensure_index()
        top_k = max(1, settings.SEMANTIC_CACHE_TOP_K)
        query = (
            Query(
                f"(@quality_status:{{ok}} @cache_scope:{{global}})=>[KNN {top_k} @embedding $vector AS distance]"
            )
            .sort_by("distance")
            .return_fields(
                "prompt",
                "response_json",
                "response_text",
                "response_type",
                "cache_scope",
                "cacheable",
                "quality_status",
                "distance",
            )
            .paging(0, top_k)
            .dialect(2)
        )
        result = self.redis.ft(self.index_name).search(
            query,
            query_params={"vector": query_vector.tobytes()},
        )
        candidates = []
        for doc in result.docs:
            payload = doc.__dict__.copy()
            payload.pop("payload", None)
            candidate = parse_candidate_payload(doc.id, payload)
            if candidate:
                candidates.append(candidate)
        return candidates

    def _embed(self, prompt: str) -> np.ndarray:
        embedding = self.embeddings.embed_query(prompt)
        return np.asarray(embedding, dtype=np.float32)

    def _exact_key(self, normalized_prompt: str) -> str:
        digest = hashlib.sha256(normalized_prompt.encode("utf-8")).hexdigest()
        return f"{self.exact_prefix}{digest}"


def normalize_query(query: str) -> str:
    """Normalize nhẹ, giữ dấu tiếng Việt để tránh mất nghĩa."""
    return re.sub(r"\s+", " ", query.strip().lower())


def is_cache_lookup_allowed(query: str) -> CacheDecision:
    normalized = normalize_query(query)
    if len(normalized) < 8:
        return CacheDecision(False, "none", "too_short")
    if "```" in query:
        return CacheDecision(False, "none", "contains_code_block")
    if any(pattern in normalized for pattern in CONTEXT_DEPENDENT_PATTERNS):
        return CacheDecision(False, "none", "context_dependent")
    if any(pattern in normalized for pattern in GENERATIVE_PATTERNS):
        return CacheDecision(False, "none", "generative_request")
    return CacheDecision(True, "global", "general_question")


def is_response_cacheable(prompt: str, response: dict[str, Any]) -> bool:
    if not is_cache_lookup_allowed(prompt).allowed:
        return False
    text = response.get("text") or ""
    response_type = response.get("type") or "rag"
    if response_type == "error" or response_type not in {"rag", "direct", "tutor"}:
        return False
    if len(text.strip()) < 40:
        return False
    normalized_text = normalize_query(text)
    return not any(pattern in normalized_text for pattern in LOW_QUALITY_PATTERNS)


def parse_candidate_payload(item_key: str, payload: dict[Any, Any]) -> Optional[dict[str, Any]]:
    if not payload:
        return None

    decoded = {
        decode_redis_value(key): decode_redis_value(value)
        for key, value in payload.items()
        if decode_redis_value(key) != "embedding"
    }
    response_json = decoded.get("response_json")
    if not response_json:
        return None

    try:
        response = json.loads(response_json)
    except json.JSONDecodeError:
        return None

    distance = float(decoded.get("distance", 1.0))
    return {
        "item_key": item_key,
        "prompt": decoded.get("prompt", ""),
        "response_json": response,
        "response_text": decoded.get("response_text", ""),
        "response_type": decoded.get("response_type", ""),
        "cache_scope": decoded.get("cache_scope", ""),
        "cacheable": decoded.get("cacheable", "true") == "true",
        "quality_status": decoded.get("quality_status", ""),
        "similarity": 1 - distance,
    }


def decode_redis_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def is_candidate_usable(candidate: dict[str, Any]) -> bool:
    return (
        candidate.get("quality_status") == "ok"
        and candidate.get("cacheable") is True
        and candidate.get("cache_scope") == "global"
        and bool(candidate.get("response_text"))
    )


def should_use_candidate(new_query: str, candidate: dict[str, Any]) -> CandidateDecision:
    if not is_candidate_usable(candidate):
        return CandidateDecision(False, "candidate_not_usable")

    similarity = candidate.get("similarity", 0.0)
    if similarity < settings.SEMANTIC_CACHE_HYBRID_THRESHOLD:
        return CandidateDecision(False, "below_vector_threshold", similarity)

    cached_query = candidate.get("prompt", "")
    if not same_intent(new_query, cached_query):
        return CandidateDecision(False, "intent_mismatch", similarity)

    if similarity >= settings.SEMANTIC_CACHE_STRONG_THRESHOLD:
        return CandidateDecision(True, "strong_semantic_hit", similarity)

    overlap = keyword_overlap(new_query, cached_query)
    if overlap >= settings.SEMANTIC_CACHE_KEYWORD_OVERLAP:
        return CandidateDecision(True, "hybrid_semantic_keyword_hit", similarity, overlap)

    return CandidateDecision(False, "keyword_overlap_too_low", similarity, overlap)


def detect_intents(query: str) -> set[str]:
    normalized = normalize_query(query)
    intents = {
        intent
        for intent, markers in INTENT_MARKERS.items()
        if any(marker in normalized for marker in markers)
    }
    return intents or {"general"}


def same_intent(new_query: str, cached_query: str) -> bool:
    new_intents = detect_intents(new_query)
    cached_intents = detect_intents(cached_query)
    if new_intents == cached_intents:
        return True
    return {frozenset(new_intents), frozenset(cached_intents)} == {
        frozenset({"definition"}),
        frozenset({"general"}),
    }


def keyword_overlap(query: str, cached_query: str) -> float:
    query_tokens = extract_keywords(query)
    cached_tokens = extract_keywords(cached_query)
    if not query_tokens or not cached_tokens:
        return 0.0
    common = query_tokens & cached_tokens
    return len(common) / min(len(query_tokens), len(cached_tokens))


def extract_keywords(query: str) -> set[str]:
    tokens = re.findall(r"[\wÀ-ỹ]+", normalize_query(query), flags=re.UNICODE)
    return {token for token in tokens if token not in VIETNAMESE_STOPWORDS}
