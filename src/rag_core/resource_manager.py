"""Quản lý tài nguyên nặng dùng chung cho RAG."""

import threading
import logging

_LOCK = threading.RLock()

_vector_db = None
_vector_retriever = None
_documents = None
_bm25_retriever = None
_hybrid_retriever = None
_tutor_reranker = None
_quiz_reranker = None
_quiz_resources = None
_rag_core = None
_tutor_chain = None

logger = logging.getLogger(__name__)


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

    docs = get_documents()
    logger.info("[prewarm] Building BM25 retriever with documents=%d", len(docs))
    return BM25KeywordSearch(docs).get_retriever()


def _build_hybrid_retriever():
    from src.retrieval.hybrid_search import HybridSearch

    return HybridSearch(get_vector_retriever(), get_bm25_retriever()).get_retriever()


def _build_tutor_reranker():
    from src.retrieval.reranking import CrossEncoderReranker

    return CrossEncoderReranker(device=_get_device())


def _build_quiz_reranker():
    from src.retrieval.reranking import CrossEncoderReranker

    return CrossEncoderReranker(device=_get_device())


def _build_rag_core():
    from src.generation.llm_model import get_llm, get_internal_llm
    from src.rag_core.offline_rag import Offline_RAG

    streaming_llm = get_llm()
    internal_llm = get_internal_llm()

    return Offline_RAG(
        streaming_llm,
        get_hybrid_retriever(),
        get_tutor_reranker(),
        llm_internal=internal_llm,
    )


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


def get_rag_core():
    global _rag_core
    if _rag_core is None:
        with _LOCK:
            if _rag_core is None:
                _rag_core = _build_rag_core()
    return _rag_core


def get_tutor_chain():
    # Trả về answer chain để tương thích với các phần cũ nếu có
    return get_rag_core().get_answer_chain()


def prewarm_all_resources():
    logger.info("[prewarm] Step 1/2: build RAG core")
    get_rag_core()
    logger.info("[prewarm] Step 2/2: build quiz resources")
    get_quiz_resources()
    logger.info("[prewarm] All resources initialized")
