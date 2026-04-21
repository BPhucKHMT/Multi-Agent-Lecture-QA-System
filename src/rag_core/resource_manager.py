"""Quản lý tài nguyên nặng dùng chung cho RAG."""

import threading

_LOCK = threading.RLock()

_vector_db = None
_vector_retriever = None
_documents = None
_bm25_retriever = None
_hybrid_retriever = None
_tutor_reranker = None
_quiz_reranker = None
_quiz_resources = None
_tutor_chain = None


def _get_device() -> str:
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


def _build_vector_db():
    from src.storage.vectorstore import VectorDB

    return VectorDB()


def _build_vector_retriever():
    return get_vector_db().get_retriever()


def _build_documents():
    return get_vector_db().get_documents()


def _build_bm25_retriever():
    from src.retrieval.keyword_search import BM25KeywordSearch

    return BM25KeywordSearch(get_documents()).get_retriever()


def _build_hybrid_retriever():
    from src.retrieval.hybrid_search import HybridSearch

    return HybridSearch(get_vector_retriever(), get_bm25_retriever()).get_retriever()


def _build_tutor_reranker():
    from src.retrieval.reranking import CrossEncoderReranker

    return CrossEncoderReranker(device=_get_device())


def _build_quiz_reranker():
    from src.retrieval.reranking import CrossEncoderReranker

    return CrossEncoderReranker(device=_get_device())


def _build_tutor_chain():
    from src.generation.llm_model import get_llm
    from src.rag_core.offline_rag import Offline_RAG

    rag_core = Offline_RAG(get_llm(), get_hybrid_retriever(), get_tutor_reranker())
    return rag_core.get_chain()


def _build_quiz_resources():
    return get_vector_retriever(), get_quiz_reranker()


def get_vector_db():
    global _vector_db
    if _vector_db is None:
        with _LOCK:
            if _vector_db is None:
                _vector_db = _build_vector_db()
    return _vector_db


def get_vector_retriever():
    global _vector_retriever
    if _vector_retriever is None:
        with _LOCK:
            if _vector_retriever is None:
                _vector_retriever = _build_vector_retriever()
    return _vector_retriever


def get_documents():
    global _documents
    if _documents is None:
        with _LOCK:
            if _documents is None:
                _documents = _build_documents()
    return _documents


def get_bm25_retriever():
    global _bm25_retriever
    if _bm25_retriever is None:
        with _LOCK:
            if _bm25_retriever is None:
                _bm25_retriever = _build_bm25_retriever()
    return _bm25_retriever


def get_hybrid_retriever():
    global _hybrid_retriever
    if _hybrid_retriever is None:
        with _LOCK:
            if _hybrid_retriever is None:
                _hybrid_retriever = _build_hybrid_retriever()
    return _hybrid_retriever


def get_tutor_reranker():
    global _tutor_reranker
    if _tutor_reranker is None:
        with _LOCK:
            if _tutor_reranker is None:
                _tutor_reranker = _build_tutor_reranker()
    return _tutor_reranker


def get_quiz_reranker():
    global _quiz_reranker
    if _quiz_reranker is None:
        with _LOCK:
            if _quiz_reranker is None:
                _quiz_reranker = _build_quiz_reranker()
    return _quiz_reranker


def get_quiz_resources():
    global _quiz_resources
    if _quiz_resources is None:
        with _LOCK:
            if _quiz_resources is None:
                _quiz_resources = _build_quiz_resources()
    return _quiz_resources


def get_tutor_chain():
    global _tutor_chain
    if _tutor_chain is None:
        with _LOCK:
            if _tutor_chain is None:
                _tutor_chain = _build_tutor_chain()
    return _tutor_chain


def prewarm_all_resources():
    get_tutor_chain()
    get_quiz_resources()
