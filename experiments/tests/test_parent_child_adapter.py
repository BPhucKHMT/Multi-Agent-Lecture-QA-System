from experiments.src.reranker.parent_child_adapter import adapt_parent_child_candidates


def test_adapt_parent_child_candidates_uses_child_for_retrieval_parent_for_context():
    child_by_id = {
        "video_a_child_10_40": {
            "doc_id": "video_a_child_10_40",
            "text": "Child precise text",
            "metadata": {
                "chunk_id": "video_a_child_10_40",
                "parent_chunk_id": "video_a_parent_0_90",
                "filename": "video_a",
                "video_url": "https://youtu.be/a",
                "start_timestamp": "0:00:10",
                "end_timestamp": "0:00:40",
            },
        }
    }
    parent_by_id = {
        "video_a_parent_0_90": {
            "doc_id": "video_a_parent_0_90",
            "text": "Parent broad context",
            "metadata": {
                "chunk_id": "video_a_parent_0_90",
                "filename": "video_a",
                "start_timestamp": "0:00:00",
                "end_timestamp": "0:01:30",
            },
        }
    }

    candidates = adapt_parent_child_candidates(
        rows=[{"doc_id": "video_a_child_10_40", "rank": 1, "score": 0.9}],
        child_by_id=child_by_id,
        parent_by_id=parent_by_id,
    )

    assert candidates == [
        {
            "doc_id": "video_a_parent_0_90",
            "rank": 1,
            "retrieval_score": 0.9,
            "text": "Parent broad context",
            "metadata": child_by_id["video_a_child_10_40"]["metadata"],
            "retrieval_doc_id": "video_a_child_10_40",
            "retrieval_text": "Child precise text",
            "context_doc_id": "video_a_parent_0_90",
            "context_text": "Parent broad context",
            "citation_doc_id": "video_a_child_10_40",
            "citation_metadata": {
                "video_url": "https://youtu.be/a",
                "start_timestamp": "0:00:10",
                "end_timestamp": "0:00:40",
            },
        }
    ]


def test_adapt_parent_child_candidates_deduplicates_parent_by_best_child_score():
    child_by_id = {
        "child_low": {
            "doc_id": "child_low",
            "text": "low",
            "metadata": {"parent_chunk_id": "parent", "video_url": "u", "start_timestamp": "0:00", "end_timestamp": "0:10"},
        },
        "child_high": {
            "doc_id": "child_high",
            "text": "high",
            "metadata": {"parent_chunk_id": "parent", "video_url": "u", "start_timestamp": "0:10", "end_timestamp": "0:20"},
        },
    }
    parent_by_id = {"parent": {"doc_id": "parent", "text": "parent context", "metadata": {}}}

    candidates = adapt_parent_child_candidates(
        rows=[
            {"doc_id": "child_low", "rank": 1, "score": 0.4},
            {"doc_id": "child_high", "rank": 2, "score": 0.8},
        ],
        child_by_id=child_by_id,
        parent_by_id=parent_by_id,
    )

    assert len(candidates) == 1
    assert candidates[0]["retrieval_doc_id"] == "child_high"
    assert candidates[0]["citation_doc_id"] == "child_high"
    assert candidates[0]["rank"] == 1
