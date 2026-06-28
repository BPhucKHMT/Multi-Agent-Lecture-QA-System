import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.src.data.chunk_loader import load_chunks
from experiments.src.qrels.overlap import should_match_evidence
from experiments.src.time_utils import timestamp_to_seconds


DEFAULT_GROUND_TRUTH = ROOT / "experiments/data/ground_truth/ground_truth_pilot.jsonl"
DEFAULT_CHUNKS_DIR = ROOT / "experiments/data/chunks/recursive"
DEFAULT_OUTPUT_DIR = ROOT / "experiments/data/processed"


def load_ground_truth(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def generate_qrels(records: list[dict], chunks: list[dict]) -> list[dict]:
    qrels_by_key: dict[tuple[str, str], int] = {}
    for record in records:
        if record.get("category") == "no_answer":
            continue
        for evidence in record.get("evidence", []):
            _add_evidence_matches(record["id"], evidence, chunks, qrels_by_key)

    return [
        {"query_id": query_id, "doc_id": doc_id, "relevance": relevance}
        for (query_id, doc_id), relevance in sorted(qrels_by_key.items())
    ]


def _add_evidence_matches(
    query_id: str,
    evidence: dict,
    chunks: list[dict],
    qrels_by_key: dict[tuple[str, str], int],
) -> None:
    evidence_start = timestamp_to_seconds(evidence.get("start_timestamp"))
    evidence_end = timestamp_to_seconds(evidence.get("end_timestamp"))
    if evidence_end <= evidence_start:
        return

    for chunk in chunks:
        metadata = chunk["metadata"]
        if not _same_video(evidence, metadata):
            continue
        if not should_match_evidence(
            evidence_start,
            evidence_end,
            metadata["start_seconds"],
            metadata["end_seconds"],
        ):
            continue
        key = (query_id, chunk["doc_id"])
        qrels_by_key[key] = max(int(evidence.get("score", 1)), qrels_by_key.get(key, 0))


def _same_video(evidence: dict, metadata: dict) -> bool:
    evidence_video_id = evidence.get("video_id")
    if evidence_video_id and evidence_video_id == metadata.get("filename"):
        return True
    return bool(evidence.get("video_url") and evidence.get("video_url") == metadata.get("video_url"))


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
    path.write_text(f"{content}\n" if content else "", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate qrels from timestamp evidence for one chunk strategy.")
    parser.add_argument("--strategy-id", default="recursive")
    parser.add_argument("--chunks-dir", type=Path, default=DEFAULT_CHUNKS_DIR)
    parser.add_argument("--ground-truth", type=Path, default=DEFAULT_GROUND_TRUTH)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    output_path = args.output or DEFAULT_OUTPUT_DIR / f"qrels_{args.strategy_id}.jsonl"
    qrels = generate_qrels(load_ground_truth(args.ground_truth), load_chunks(args.chunks_dir, strategy_id=args.strategy_id))
    write_jsonl(output_path, qrels)
    print(f"Generated {output_path} with {len(qrels)} relevance mappings.")


if __name__ == "__main__":
    main()
