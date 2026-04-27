import re
import unicodedata

from src.rag_core import resource_manager

_LECTURE_SIGNALS = (
    "bài giảng",
    "lecture",
    "theo slide",
    "trích dẫn",
    "citation",
    "nguồn",
    "machine learning",
    "deep learning",
    "trí tuệ nhân tạo",
)

_SCORE_KEYS = ("score", "relevance_score", "rerank_score", "cross_encoder_score")
_MIN_RERANK_SCORE = -2.0


def _normalize_for_matching(text: str) -> str:
    lowered = text.lower().replace("đ", "d")
    normalized = unicodedata.normalize("NFKD", lowered)
    no_diacritics = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    collapsed = re.sub(r"[^a-z0-9]+", " ", no_diacritics)
    return " ".join(collapsed.split())


_NORMALIZED_LECTURE_SIGNALS = tuple(_normalize_for_matching(signal) for signal in _LECTURE_SIGNALS)


def should_use_rag(query: str) -> bool:
    """Kiểm tra query có tín hiệu cần grounding từ bài giảng/citation hay không."""
    if not isinstance(query, str):
        return False
    normalized_query = _normalize_for_matching(query)
    if not normalized_query:
        return False
    padded_query = f" {normalized_query} "
    return any(f" {signal} " in padded_query for signal in _NORMALIZED_LECTURE_SIGNALS)


def _extract_score(doc):
    for key in _SCORE_KEYS:
        value = getattr(doc, key, None)
        if isinstance(value, (int, float)):
            return float(value)
    metadata = getattr(doc, "metadata", {}) or {}
    if isinstance(metadata, dict):
        for key in _SCORE_KEYS:
            value = metadata.get(key)
            if isinstance(value, (int, float)):
                return float(value)
    return None


def retrieve_lecture_context(query: str, top_k: int = 3) -> tuple[str, list]:
    """
    Lấy context từ RAG phục vụ coding.
    Trả về (text_context, metadata_list).
    """
    try:
        retriever = resource_manager.get_hybrid_retriever()
        reranker = resource_manager.get_tutor_reranker()

        if hasattr(retriever, "invoke"):
            docs = retriever.invoke(query)
        else:
            docs = retriever.get_relevant_documents(query)
        if not docs:
            return "", []

        reranked_docs = reranker.rerank(docs, query, top_k=max(1, int(top_k)))
        if not reranked_docs:
            return "", []

        context_parts = []
        metadata_list = []
        for doc in reranked_docs:
            score = _extract_score(doc)
            if score is not None and score < _MIN_RERANK_SCORE:
                continue
            
            content = getattr(doc, "page_content", "")
            if isinstance(content, str) and content.strip():
                context_parts.append(content.strip())
                # Trích xuất metadata cần thiết cho frontend
                meta = getattr(doc, "metadata", {}) or {}
                metadata_list.append({
                    "video_url": meta.get("video_url", ""),
                    "title": meta.get("title", ""),
                    "filename": meta.get("filename", ""),
                    "start_timestamp": meta.get("start_timestamp", ""),
                    "end_timestamp": meta.get("end_timestamp", ""),
                    "confidence": "high"
                })

        if not context_parts:
            return "", []
            
        return "\n---\n".join(context_parts), metadata_list
    except Exception:
        return "", []
