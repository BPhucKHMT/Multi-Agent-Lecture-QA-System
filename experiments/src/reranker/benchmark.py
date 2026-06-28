import csv
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Set

from experiments.src.data.chunk_loader import load_chunks
from experiments.src.data.qrels_loader import load_dynamic_qrels, load_qrels
from experiments.src.evaluation.metrics import mean_metrics
from experiments.src.reranker.candidate_set import build_candidates, write_json, write_jsonl
from experiments.src.reranker.models import ModelLoadResult, RerankerModel, load_reranker


def run_reranker_benchmark(config: Dict[str, Any], limit: Optional[int] = None, only: Optional[Set[str]] = None) -> Path:
    run_dir = build_run_dir(Path(config["run_root"]), config["strategy_id"])
    write_json(run_dir / "config.json", config)
    chunks = load_chunks(config["chunks_dir"], strategy_id=config["strategy_id"])
    candidates, candidate_metrics = build_candidates(config, run_dir, limit)
    candidates_by_embedding = group_candidates_by_embedding(candidates)
    qrels = load_strategy_qrels(config, chunks)
    rows = []
    for model_config in config.get("models", []):
        if only and model_config["name"] not in only:
            continue
        if not model_config.get("enabled", True):
            rows.append(write_skip(run_dir, model_config, "disabled", model_config.get("optional_reason", "disabled")))
            continue
        for lane_name in model_config.get("lanes", config["lanes"].keys()):
            lane_config = config["lanes"][lane_name]
            loaded = load_reranker(model_config, lane_config, resolve_device(config.get("device", "auto")))
            if loaded.model is None:
                rows.append(write_skip(run_dir, model_config, loaded.status, loaded.reason or "model load failed", lane_name))
                continue
            for pool_size in lane_config["candidate_pool_sizes"]:
                for embedding_candidates in candidates_by_embedding.values():
                    rows.append(run_model_lane(run_dir, config, model_config, loaded, lane_name, int(pool_size), embedding_candidates, qrels))
            # Clean up GPU/RAM memory for the loaded model
            del loaded
            import gc
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
    write_summary(run_dir, rows, candidate_metrics, config)
    append_registry(Path(config["registry_path"]), run_dir, rows, config)
    return run_dir


def group_candidates_by_embedding(candidates: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in candidates:
        grouped.setdefault(str(record.get("embedding_model", "unknown")), []).append(record)
    return grouped


def load_strategy_qrels(config: dict[str, Any], chunks: list[dict[str, Any]]) -> dict[str, Any]:
    if config["strategy_id"] == "parent_child_180s_45s":
        return load_qrels(config["qrels_path"])
    return load_dynamic_qrels(config["query_path"], chunks)


def run_model_lane(
    run_dir: Path,
    config: dict[str, Any],
    model_config: dict[str, Any],
    loaded: ModelLoadResult,
    lane_name: str,
    pool_size: int,
    candidates: list[dict[str, Any]],
    qrels: dict[str, dict[str, int]],
) -> dict[str, Any]:
    assert loaded.model is not None
    embedding_model = str(candidates[0].get("embedding_model", "unknown")) if candidates else "unknown"
    model_dir = run_dir / "models" / slugify(model_config["name"]) / slugify(embedding_model) / lane_name / f"top_{pool_size}"
    results, timings = rerank_candidates(loaded.model, candidates, pool_size)
    rankings = {f"{record['embedding_model']}::{record['query_id']}": [item["doc_id"] for item in record["results"]] for record in results}
    expanded_qrels = {f"{record['embedding_model']}::{record['query_id']}": qrels.get(record["query_id"], {}) for record in results}
    metric_config = config.get("metrics", {})
    metrics = mean_metrics(
        rankings,
        expanded_qrels,
        recall_at=metric_config.get("recall_at", [10]),
        mrr_at=metric_config.get("mrr_at", [10]),
        ndcg_at=metric_config.get("ndcg_at", [10]),
        precision_at=metric_config.get("precision_at", [1]),
        map_at=metric_config.get("map_at", [10]),
    )
    latency = summarize_latency(timings, config.get("latency_gates", {}))
    manifest = {
        "component": "reranker",
        "task": "reranker_benchmark",
        "model": model_config["name"],
        "model_type": model_config.get("type"),
        "embedding_model": embedding_model,
        "lane": lane_name,
        "candidate_pool_size": pool_size,
        "status": loaded.status,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_jsonl(model_dir / "reranked_results.jsonl", results)
    write_json(model_dir / "metrics.json", metrics)
    write_json(model_dir / "latency.json", latency)
    write_json(model_dir / "manifest.json", manifest)
    return {
        "model": model_config["name"],
        "embedding_model": embedding_model,
        "lane": lane_name,
        "candidate_pool_size": pool_size,
        "status": loaded.status,
        "metrics_path": str(model_dir / "metrics.json"),
        "latency_path": str(model_dir / "latency.json"),
        **metrics,
        **latency,
    }


def rerank_candidates(model: RerankerModel, records: list[dict[str, Any]], pool_size: int) -> tuple[list[dict[str, Any]], list[float]]:
    output = []
    timings = []
    for record in records:
        selected = record["candidates"][:pool_size]
        start = time.perf_counter()
        scores = model.score_pairs(record["query"], [candidate["text"] for candidate in selected])
        elapsed_ms = (time.perf_counter() - start) * 1000
        timings.append(elapsed_ms)
        reranked = []
        for candidate, score in zip(selected, scores, strict=True):
            reranked.append({**candidate, "reranker_score": float(score), "original_rank": candidate["rank"]})
        reranked.sort(key=lambda item: (-item["reranker_score"], item["original_rank"]))
        output.append(
            {
                "query_id": record["query_id"],
                "query": record["query"],
                "embedding_model": record.get("embedding_model", "unknown"),
                "results": [to_result(index, item) for index, item in enumerate(reranked, start=1)],
            }
        )
    return output, timings


def to_result(rank: int, item: dict[str, Any]) -> dict[str, Any]:
    result = {
        "rank": rank,
        "doc_id": item["doc_id"],
        "original_rank": item["original_rank"],
        "retrieval_score": item["retrieval_score"],
        "reranker_score": item["reranker_score"],
        "metadata": item["metadata"],
    }
    for key in ("retrieval_doc_id", "context_doc_id", "citation_doc_id", "citation_metadata"):
        if key in item:
            result[key] = item[key]
    return result


def summarize_latency(values: list[float], gates: dict[str, Any]) -> dict[str, Any]:
    if not values:
        return {"latency_count": 0, "latency_status": "no_data"}
    sorted_values = sorted(values)
    p95 = percentile(sorted_values, 95)
    target = float(gates.get("demo_target_p95_ms", 800))
    hard_cap = float(gates.get("demo_hard_cap_p95_ms", 1500))
    status = "pass"
    if p95 > hard_cap:
        status = "reject"
    elif p95 > target:
        status = "warn"
    return {
        "latency_count": len(values),
        "latency_mean_ms": statistics.mean(values),
        "latency_p50_ms": percentile(sorted_values, 50),
        "latency_p95_ms": p95,
        "latency_max_ms": max(values),
        "latency_status": status,
    }


def percentile(sorted_values: list[float], percentile_value: int) -> float:
    if len(sorted_values) == 1:
        return sorted_values[0]
    index = (len(sorted_values) - 1) * percentile_value / 100
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = index - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def write_skip(run_dir: Path, model_config: dict[str, Any], status: str, reason: str, lane_name: str = "all") -> dict[str, Any]:
    row = {
        "model": model_config["name"],
        "lane": lane_name,
        "candidate_pool_size": None,
        "status": status,
        "skip_reason": reason,
    }
    write_json(run_dir / "models" / slugify(model_config["name"]) / lane_name / "skip.json", row)
    return row


def write_summary(run_dir: Path, rows: list[dict[str, Any]], candidate_metrics: dict[str, Any], config: dict[str, Any]) -> None:
    fields = sorted({key for row in rows for key in row})
    with (run_dir / "summary.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    lines = ["# Reranker Benchmark Summary", "", "## Candidate Metrics", ""]
    for key, value in candidate_metrics.items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Runs", "", "| Embedding | Reranker | Pool | Status | NDCG@10 | MRR@10 | Recall@40 | P95 ms | Latency |", "|---|---|---:|---|---:|---:|---:|---:|---|"])
    for row in rows:
        lines.append(
            "| {embedding} | {model} | {pool} | {status} | {ndcg} | {mrr} | {recall} | {p95} | {latency} |".format(
                embedding=row.get("embedding_model", ""),
                model=row.get("model", ""),
                lane=row.get("lane", ""),
                pool=row.get("candidate_pool_size", ""),
                status=row.get("status", ""),
                ndcg=row.get("ndcg@10", ""),
                mrr=row.get("mrr@10", ""),
                recall=row.get("recall@40", ""),
                p95=row.get("latency_p95_ms", ""),
                latency=row.get("latency_status", ""),
            )
        )
    lines.extend(["", "## Config", "", f"- Dataset: `{config['dataset_version']}`", f"- Strategy: `{config['strategy_id']}`"])
    (run_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_registry(path: Path, run_dir: Path, rows: list[dict[str, Any]], config: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "component": "reranker",
        "task": "reranker_benchmark",
        "dataset_version": config["dataset_version"],
        "strategy_id": config["strategy_id"],
        "run_dir": str(run_dir),
        "summary_path": str(run_dir / "summary.md"),
        "status": "completed",
        "completed_runs": sum(1 for row in rows if row.get("status") == "completed"),
        "skipped_runs": sum(1 for row in rows if str(row.get("status", "")).startswith("skipped") or row.get("status") == "disabled"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")


def build_run_dir(root: Path, strategy_id: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = root / strategy_id / stamp
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def resolve_device(device: str) -> Optional[str]:
    if device == "auto":
        try:
            import torch

            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return None
    if device in {"cpu", "cuda"}:
        return device
    return None


def slugify(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value).strip("_").lower()
