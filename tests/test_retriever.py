import os
import sys
from pathlib import Path

from langchain.schema import Document

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, os.fspath(PROJECT_ROOT))

from src.rag_core.resource_manager import get_hybrid_retriever

QUERY = "thành tựu cnn"
TOP_K = 5
SNIPPET_CHARS = 220


def retrieve_documents(query: str = QUERY, top_k: int = TOP_K) -> list[Document]:
    retriever = get_hybrid_retriever()
    documents = retriever.invoke(query)
    if not isinstance(documents, list):
        return []
    return documents[: max(top_k, 0)]


def _to_snippet(text: str) -> str:
    compact_text = " ".join(str(text).split())
    if len(compact_text) <= SNIPPET_CHARS:
        return compact_text
    return compact_text[:SNIPPET_CHARS] + "..."


def _print_documents(documents: list[Document]) -> None:
    for index, doc in enumerate(documents, start=1):
        metadata = doc.metadata or {}
        print(f"\n[{index}] {metadata.get('title', '(không có title)')}")
        print(f"    filename: {metadata.get('filename', '')}")
        print(f"    video_url: {metadata.get('video_url', '')}")
        print(
            "    timestamp: "
            f"{metadata.get('start_timestamp', '')} -> {metadata.get('end_timestamp', '')}"
        )
        print(f"    snippet: {_to_snippet(doc.page_content)}")


def main() -> list[Document]:
    print(f"Query: {QUERY}")
    print(f"Retriever: Hybrid (BM25 + Vector) | Top K: {TOP_K}")
    try:
        documents = retrieve_documents()
    except Exception as error:
        print(f"Lỗi khi truy vấn retriever: {error}")
        return []

    if not documents:
        print("Không tìm thấy document nào.")
        return []

    print(f"Tìm thấy {len(documents)} documents.")
    _print_documents(documents)
    return documents


def test_retrieve_documents_limits_top_k(monkeypatch):
    class _FakeRetriever:
        def invoke(self, _query):
            return [
                Document(page_content=f"doc-{index}", metadata={"title": f"title-{index}"})
                for index in range(7)
            ]

    monkeypatch.setattr(__import__(__name__), "get_hybrid_retriever", lambda: _FakeRetriever())

    docs = retrieve_documents(query="thành tựu cnn", top_k=5)
    assert len(docs) == 5


if __name__ == "__main__":
    main()
