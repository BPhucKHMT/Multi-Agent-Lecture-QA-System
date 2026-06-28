import argparse
import json
from pathlib import Path
from typing import Any

MISSING_RANK = 99


def audit_failures(
    baseline_path: Path,
    reranked_path: Path,
    qrels_path: Path,
    output_path: Path,
    limit: int = 20,
) -> dict[str, int]:
    baseline_records = {record["query_id"]: record for record in read_jsonl(baseline_path)}
    reranked_records = {record["query_id"]: record for record in read_jsonl(reranked_path)}
    qrels = load_qrels(qrels_path)

    rows = []
    for query_id, baseline in baseline_records.items():
        reranked = reranked_records.get(query_id)
        relevant_docs = qrels.get(query_id, {})
        if not reranked or not relevant_docs:
            continue

        baseline_rank = first_relevant_rank(baseline, relevant_docs)
        reranked_rank = first_relevant_rank(reranked, relevant_docs)
        if reranked_rank <= baseline_rank:
            continue

        gold_chunks = [to_chunk_summary(item) for item in baseline["results"] if item["doc_id"] in relevant_docs]
        top_reranked = reranked["results"][0] if reranked.get("results") else None
        rows.append(
            {
                "query_id": query_id,
                "query": baseline.get("query", ""),
                "baseline_first_relevant_rank": baseline_rank,
                "reranked_first_relevant_rank": reranked_rank,
                "rank_delta": reranked_rank - baseline_rank,
                "top_reranked": to_chunk_summary(top_reranked) if top_reranked else None,
                "top_reranked_overlap_with_gold_seconds": max_overlap_seconds(top_reranked, gold_chunks),
                "gold_chunks": gold_chunks,
                "baseline_top": [to_chunk_summary(item) for item in baseline.get("results", [])[:5]],
                "reranked_top": [to_chunk_summary(item) for item in reranked.get("results", [])[:5]],
            }
        )

    rows.sort(key=lambda row: (-row["rank_delta"], row["query_id"]))
    write_jsonl(output_path, rows[:limit])
    return {"worsened_count": len(rows), "written_count": min(len(rows), limit)}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_qrels(path: Path) -> dict[str, dict[str, int]]:
    qrels: dict[str, dict[str, int]] = {}
    for record in read_jsonl(path):
        qrels.setdefault(record["query_id"], {})[record["doc_id"]] = int(record["relevance"])
    return qrels


def first_relevant_rank(record: dict[str, Any], relevant_docs: dict[str, int]) -> int:
    for rank, item in enumerate(record.get("results", [])[:10], start=1):
        if item["doc_id"] in relevant_docs:
            return rank
    return MISSING_RANK


def to_chunk_summary(item: dict[str, Any] | None) -> dict[str, Any]:
    if not item:
        return {}
    metadata = item.get("metadata", {})
    return {
        "doc_id": item.get("doc_id"),
        "rank": item.get("rank"),
        "original_rank": item.get("original_rank"),
        "start_seconds": metadata.get("start_seconds"),
        "end_seconds": metadata.get("end_seconds"),
        "video_id": metadata.get("filename"),
    }


def max_overlap_seconds(item: dict[str, Any] | None, gold_chunks: list[dict[str, Any]]) -> int:
    if not item:
        return 0
    metadata = item.get("metadata", {})
    start = metadata.get("start_seconds")
    end = metadata.get("end_seconds")
    video_id = metadata.get("filename")
    if start is None or end is None or video_id is None:
        return 0
    return max(
        (
            overlap_seconds(start, end, gold["start_seconds"], gold["end_seconds"])
            for gold in gold_chunks
            if gold.get("video_id") == video_id
        ),
        default=0,
    )


def overlap_seconds(start_a: int, end_a: int, start_b: int | None, end_b: int | None) -> int:
    if start_b is None or end_b is None:
        return 0
    return max(0, min(end_a, end_b) - max(start_a, start_b))


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
    path.write_text(f"{content}\n" if content else "", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Xuất các query mà reranker làm first relevant rank tệ hơn baseline.")
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--reranked", type=Path, required=True)
    parser.add_argument("--qrels", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    summary = audit_failures(args.baseline, args.reranked, args.qrels, args.output, args.limit)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
