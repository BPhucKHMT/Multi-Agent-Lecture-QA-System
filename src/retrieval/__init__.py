"""Module retrieval theo layout src."""


def __getattr__(name: str):
    if name == "HybridSearch":
        from .hybrid_search import HybridSearch

        return HybridSearch
    if name == "BM25KeywordSearch":
        from .keyword_search import BM25KeywordSearch

        return BM25KeywordSearch
    if name in {"CrossEncoderReranker", "load_reranker", "resolve_backend"}:
        from . import reranking

        return getattr(reranking, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "HybridSearch",
    "BM25KeywordSearch",
    "CrossEncoderReranker",
    "load_reranker",
    "resolve_backend",
]
