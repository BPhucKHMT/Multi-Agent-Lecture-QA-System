import json
from pathlib import Path

from experiments.scripts.audit_reranker_failures import audit_failures


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n", encoding="utf-8")


def test_audit_failures_exports_rank_delta_and_timestamp_overlap(tmp_path):
    baseline_path = tmp_path / "baseline.jsonl"
    reranked_path = tmp_path / "reranked.jsonl"
    qrels_path = tmp_path / "qrels.jsonl"
    output_path = tmp_path / "audit.jsonl"

    base_record = {
        "query_id": "q1",
        "query": "hỏi về attention",
        "results": [
            {
                "rank": 1,
                "doc_id": "video_0_30",
                "metadata": {"filename": "video", "start_seconds": 0, "end_seconds": 30},
            },
            {
                "rank": 2,
                "doc_id": "video_30_60",
                "metadata": {"filename": "video", "start_seconds": 30, "end_seconds": 60},
            },
            {
                "rank": 3,
                "doc_id": "other_30_60",
                "metadata": {"filename": "other", "start_seconds": 30, "end_seconds": 60},
            },
        ],
    }
    reranked_record = {
        "query_id": "q1",
        "query": "hỏi về attention",
        "results": [
            {
                "rank": 1,
                "doc_id": "video_30_60",
                "metadata": {"filename": "video", "start_seconds": 30, "end_seconds": 60},
            },
            {
                "rank": 2,
                "doc_id": "video_0_30",
                "metadata": {"filename": "video", "start_seconds": 0, "end_seconds": 30},
            },
        ],
    }
    _write_jsonl(baseline_path, [base_record])
    _write_jsonl(reranked_path, [reranked_record])
    _write_jsonl(
        qrels_path,
        [
            {"query_id": "q1", "doc_id": "video_0_30", "relevance": 3},
            {"query_id": "q1", "doc_id": "other_30_60", "relevance": 2},
        ],
    )

    summary = audit_failures(
        baseline_path=baseline_path,
        reranked_path=reranked_path,
        qrels_path=qrels_path,
        output_path=output_path,
        limit=10,
    )

    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert summary["worsened_count"] == 1
    assert rows[0]["baseline_first_relevant_rank"] == 1
    assert rows[0]["reranked_first_relevant_rank"] == 2
    assert rows[0]["top_reranked_overlap_with_gold_seconds"] == 0
    assert rows[0]["gold_chunks"][0]["doc_id"] == "video_0_30"
