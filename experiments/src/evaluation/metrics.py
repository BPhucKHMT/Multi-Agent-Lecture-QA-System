import math
import json
from pathlib import Path
from collections.abc import Sequence
from typing import Dict, Optional, Union

from experiments.src.time_utils import timestamp_to_seconds


def parse_doc_id(doc_id: str):
    parts = doc_id.rsplit("_", 2)
    if len(parts) != 3:
        return None
    video_id, start_text, end_text = parts
    if video_id.endswith("_parent"):
        video_id = video_id[:-7]
    elif video_id.endswith("_child"):
        video_id = video_id[:-6]
    try:
        return video_id, int(float(start_text)), int(float(end_text))
    except ValueError:
        return None


def _load_evidence_queries() -> dict:
    possible_paths = [
        Path("experiments/data/ground_truth/ground_truth_pilot.jsonl"),
        Path("../data/ground_truth/ground_truth_pilot.jsonl"),
        Path("data/ground_truth/ground_truth_pilot.jsonl"),
        Path(__file__).resolve().parent.parent.parent / "data/ground_truth/ground_truth_pilot.jsonl",
    ]
    for path in possible_paths:
        if path.exists():
            queries = {}
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("category") == "no_answer":
                    continue
                evidence = []
                for item in record.get("evidence", []):
                    start = timestamp_to_seconds(item.get("start_timestamp"))
                    end = timestamp_to_seconds(item.get("end_timestamp"))
                    video_id = item.get("video_id")
                    if video_id and end > start:
                        evidence.append((video_id, start, end))
                if evidence:
                    queries[record["id"]] = evidence
            return queries
    return {}


def _recall_new_at(ranking: Sequence[str], evidence: list[tuple[str, int, int]], k: int) -> float:
    if not evidence:
        return 0.0
    retrieved = []
    for doc_id in ranking[:k]:
        parsed = parse_doc_id(doc_id)
        if parsed:
            retrieved.append(parsed)
    covered = 0
    for gt_video, gt_start, gt_end in evidence:
        if any(
            pred_video == gt_video and max(pred_start, gt_start) < min(pred_end, gt_end)
            for pred_video, pred_start, pred_end in retrieved
        ):
            covered += 1
    return covered / len(evidence)


def mean_metrics(
    rankings: Dict[str, Sequence[str]],
    qrels: Dict[str, Dict[str, int]],
    recall_at: Sequence[int],
    mrr_at: Sequence[int],
    ndcg_at: Sequence[int],
    precision_at: Optional[Sequence[int]] = None,
    map_at: Optional[Sequence[int]] = None,
    hit_at: Optional[Sequence[int]] = None,
    recall_new_at: Optional[Sequence[int]] = None,
    aliases: Optional[Dict[str, str]] = None,
) -> Dict[str, Union[float, int]]:
    answerable_queries = [query_id for query_id in rankings if query_id in qrels and len(qrels[query_id]) > 0]
    metrics: Dict[str, Union[float, int]] = {
        "query_count": len(answerable_queries),
        "no_qrels_query_count": len(rankings) - len(answerable_queries),
    }

    evidence_queries = _load_evidence_queries()

    for k in recall_at:
        recall_vals = []
        for q in answerable_queries:
            if evidence_queries and q in evidence_queries:
                recall_vals.append(_recall_new_at(rankings[q], evidence_queries[q], k))
            else:
                recall_vals.append(_recall_at(rankings[q], qrels[q], k))
        metrics[f"recall@{k}"] = _mean(recall_vals)

        if evidence_queries:
            valid_queries = [q for q in answerable_queries if q in evidence_queries]
            if valid_queries:
                metrics[f"recall_new@{k}"] = _mean([
                    _recall_new_at(rankings[q], evidence_queries[q], k)
                    for q in valid_queries
                ])
            else:
                metrics[f"recall_new@{k}"] = 0.0

    for k in mrr_at:
        metrics[f"mrr@{k}"] = _mean([_mrr_at(rankings[q], qrels[q], k) for q in answerable_queries])
    for k in ndcg_at:
        metrics[f"ndcg@{k}"] = _mean([_ndcg_at(rankings[q], qrels[q], k) for q in answerable_queries])
    for k in precision_at or []:
        metrics[f"precision@{k}"] = _mean([_precision_at(rankings[q], qrels[q], k) for q in answerable_queries])
    for k in map_at or []:
        metrics[f"map@{k}"] = _mean([_average_precision_at(rankings[q], qrels[q], k) for q in answerable_queries])
    for k in hit_at or []:
        metrics[f"hit@{k}"] = _mean([_hit_at(rankings[q], qrels[q], k) for q in answerable_queries])

    # Compute recall_new@k for any other requested values
    recall_new_vals = recall_new_at if recall_new_at is not None else [40]
    for k in recall_new_vals:
        if f"recall_new@{k}" not in metrics:
            if evidence_queries:
                valid_queries = [q for q in answerable_queries if q in evidence_queries]
                if valid_queries:
                    metrics[f"recall_new@{k}"] = _mean([
                        _recall_new_at(rankings[q], evidence_queries[q], k)
                        for q in valid_queries
                    ])
                else:
                    metrics[f"recall_new@{k}"] = 0.0
            else:
                metrics[f"recall_new@{k}"] = 0.0

    for alias, source in (aliases or {}).items():
        if source.startswith("hit@") and source not in metrics:
            k = int(source.split("@", 1)[1])
            metrics[source] = _mean([_hit_at(rankings[q], qrels[q], k) for q in answerable_queries])
        elif source.startswith("recall_new@") and source not in metrics:
            k = int(source.split("@", 1)[1])
            if evidence_queries:
                valid_queries = [q for q in answerable_queries if q in evidence_queries]
                if valid_queries:
                    metrics[source] = _mean([
                        _recall_new_at(rankings[q], evidence_queries[q], k)
                        for q in valid_queries
                    ])
                else:
                    metrics[source] = 0.0
        metrics[alias] = metrics.get(source, 0.0)

    return metrics



def _unique_ranking(ranking: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for doc_id in ranking:
        if doc_id in seen:
            continue
        seen.add(doc_id)
        unique.append(doc_id)
    return unique


def _recall_at(ranking: Sequence[str], relevant_docs: dict[str, int], k: int) -> float:
    if not relevant_docs:
        return 0.0
    unique_ranking = _unique_ranking(ranking)
    hits = sum(1 for doc_id in unique_ranking[:k] if doc_id in relevant_docs)
    return hits / len(relevant_docs)


def _precision_at(ranking: Sequence[str], relevant_docs: dict[str, int], k: int) -> float:
    if k <= 0:
        return 0.0
    unique_ranking = _unique_ranking(ranking)
    hits = sum(1 for doc_id in unique_ranking[:k] if doc_id in relevant_docs)
    return hits / k


def _hit_at(ranking: Sequence[str], relevant_docs: dict[str, int], k: int) -> float:
    if k <= 0:
        return 0.0
    unique_ranking = _unique_ranking(ranking)
    return 1.0 if any(doc_id in relevant_docs for doc_id in unique_ranking[:k]) else 0.0


def _mrr_at(ranking: Sequence[str], relevant_docs: dict[str, int], k: int) -> float:
    unique_ranking = _unique_ranking(ranking)
    for index, doc_id in enumerate(unique_ranking[:k], start=1):
        if doc_id in relevant_docs:
            return 1 / index
    return 0.0


def _average_precision_at(ranking: Sequence[str], relevant_docs: dict[str, int], k: int) -> float:
    if not relevant_docs:
        return 0.0
    hits = 0
    precision_sum = 0.0
    unique_ranking = _unique_ranking(ranking)
    for index, doc_id in enumerate(unique_ranking[:k], start=1):
        if doc_id in relevant_docs:
            hits += 1
            precision_sum += hits / index
    return precision_sum / min(len(relevant_docs), k)


def _ndcg_at(ranking: Sequence[str], relevant_docs: dict[str, int], k: int) -> float:
    unique_ranking = _unique_ranking(ranking)
    dcg = _dcg([relevant_docs.get(doc_id, 0) for doc_id in unique_ranking[:k]])
    ideal = _dcg(sorted(relevant_docs.values(), reverse=True)[:k])
    return dcg / ideal if ideal else 0.0


def _dcg(relevances: Sequence[int]) -> float:
    return sum((2**rel - 1) / math.log2(index + 1) for index, rel in enumerate(relevances, start=1))


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0
