from experiments.src.benchmark.hybrid_retrieval import BM25Index, enriched_text, weighted_rrf


def test_enriched_text_includes_ocr_context():
    chunk = {"text": "machine learning", "metadata": {"ocr_content": "gradient descent"}}

    text = enriched_text(chunk)

    assert "machine learning" in text
    assert "[OCR Context]: gradient descent" in text


def test_bm25_uses_ocr_content_for_matching():
    chunks = [
        {"doc_id": "d1", "text": "intro", "metadata": {"ocr_content": "gradient descent"}},
        {"doc_id": "d2", "text": "intro", "metadata": {"ocr_content": "decision tree"}},
    ]

    ranking = BM25Index(chunks).rank("gradient", top_k=2)

    assert ranking[0] == "d1"


def test_weighted_rrf_combines_dense_and_bm25_with_fixed_weights():
    fused = weighted_rrf(
        rankings=[["dense_first", "shared"], ["bm25_first", "shared"]],
        weights=[0.5, 0.5],
        top_k=3,
    )

    assert [doc_id for doc_id, _ in fused] == ["shared", "bm25_first", "dense_first"]
