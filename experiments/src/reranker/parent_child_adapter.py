from typing import Any


def adapt_parent_child_candidates(
    rows: list[dict[str, Any]],
    child_by_id: dict[str, dict[str, Any]],
    parent_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    best_by_parent: dict[str, dict[str, Any]] = {}

    for row in rows:
        child = child_by_id.get(row["doc_id"])
        if not child:
            continue

        child_metadata = child["metadata"]
        parent_id = child_metadata.get("parent_chunk_id")
        parent = parent_by_id.get(parent_id)
        if not parent:
            continue

        candidate = to_candidate(row, child, parent)
        current = best_by_parent.get(parent_id)
        if current is None or candidate["retrieval_score"] > current["retrieval_score"]:
            best_by_parent[parent_id] = candidate

    candidates = sorted(best_by_parent.values(), key=lambda candidate: candidate["retrieval_score"], reverse=True)
    for rank, candidate in enumerate(candidates, start=1):
        candidate["rank"] = rank
    return candidates


def to_candidate(row: dict[str, Any], child: dict[str, Any], parent: dict[str, Any]) -> dict[str, Any]:
    child_metadata = child["metadata"]
    return {
        "doc_id": parent["doc_id"],
        "rank": int(row["rank"]),
        "retrieval_score": float(row.get("score", 0.0)),
        "text": parent["text"],
        "metadata": child_metadata,
        "retrieval_doc_id": child["doc_id"],
        "retrieval_text": child["text"],
        "context_doc_id": parent["doc_id"],
        "context_text": parent["text"],
        "citation_doc_id": child["doc_id"],
        "citation_metadata": {
            "video_url": child_metadata.get("video_url"),
            "start_timestamp": child_metadata.get("start_timestamp"),
            "end_timestamp": child_metadata.get("end_timestamp"),
        },
    }
