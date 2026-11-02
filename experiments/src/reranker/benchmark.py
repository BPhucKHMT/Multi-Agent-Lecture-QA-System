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


def run_reranker_benchmark(
    config: Dict[str, Any],
    limit: Optional[int] = None,
    only: Optional[Set[str]] = None,
    offset: int = 0,
) -> Path:
    run_dir = build_run_dir(Path(config["run_root"]), config["strategy_id"])
    run_config = {
        **config,
        "query_limit": limit,
        "query_offset": offset,
    }
    write_json(run_dir / "config.json", run_config)
    chunks = load_chunks(config["chunks_dir"], strategy_id=config["strategy_id"])
    candidate_limit = offset + limit if limit is not None else None
    candidates, candidate_metrics = build_candidates(
        config,
        run_dir,
        candidate_limit,
    )
    candidates = select_candidate_records(
        candidates,
        offset=offset,
        limit=limit,
    )
    candidates_by_embedding = group_candidates_by_embedding(candidates)
    candidate_metrics["benchmark_query_offset"] = offset
    candidate_metrics["benchmark_query_count"] = len(candidates)
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
                    rows.append(run_model_lane(run_dir, run_config, model_config, loaded, lane_name, int(pool_size), embedding_candidates, qrels))
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
    rows = apply_candidate_pool_gates(
        rows,
        config.get("candidate_pool_gates", {}),
    )
    write_summary(run_dir, rows, candidate_metrics, run_config)
    if run_config.get("require_completed_models"):
        ensure_required_runs_completed(rows)
    append_registry(Path(config["registry_path"]), run_dir, rows, run_config)
    return run_dir


def group_candidates_by_embedding(candidates: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in candidates:
        grouped.setdefault(str(record.get("embedding_model", "unknown")), []).append(record)
    return grouped


def select_candidate_records(
    records: list[dict[str, Any]],
    *,
    offset: int = 0,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    if offset < 0:
        raise ValueError("offset phải lớn hơn hoặc bằng 0")
    if limit is not None and limit < 1:
        raise ValueError("limit phải lớn hơn 0")

    selected = []
    source_positions: dict[str, int] = {}
    for record in records:
        source = str(record.get("embedding_model", "unknown"))
        position = source_positions.get(source, 0)
        source_positions[source] = position + 1
        if position < offset:
            continue
        if limit is not None and position >= offset + limit:
            continue
        selected.append(record)
    return selected


def ensure_required_runs_completed(rows: list[dict[str, Any]]) -> None:
    failed = [
        row
        for row in rows
        if row.get("status") != "completed"
    ]
    if not failed:
        return
    details = "; ".join(
        f"{row.get('model', 'unknown')}: "
        f"{row.get('skip_reason', row.get('status', 'unknown'))}"
        for row in failed
    )
    raise RuntimeError(f"Reranker benchmark không hoàn tất: {details}")


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
    embedding_model = (
        str(candidates[0].get("embedding_model", "unknown"))
        if candidates
        else "unknown"
    )
    model_dir = (
        run_dir
        / "models"
        / slugify(model_config["name"])
        / slugify(embedding_model)
        / lane_name
        / f"top_{pool_size}"
    )
    progress_label = (
        f"model={model_config['name']} embedding={embedding_model} "
        f"lane={lane_name} pool={pool_size}"
    )
    if candidates:
        warmup_candidates = candidates[0]["candidates"][:pool_size]
        loaded.model.score_pairs(
            candidates[0]["query"],
            [candidate["text"] for candidate in warmup_candidates],
        )
    results, timings = rerank_candidates(
        loaded.model,
        candidates,
        pool_size,
        progress_label=progress_label,
    )
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
        hit_at=metric_config.get("hit_at", [5]),
    )
    latency = summarize_latency(timings, config.get("latency_gates", {}))
    manifest = {
        "component": "reranker",
        "task": "reranker_benchmark",
        "model": model_config["name"],
        "model_type": model_config.get("type"),
        "backend": model_config.get("backend"),
        "batch_size": model_config.get("batch_size"),
        "embedding_model": embedding_model,
        "lane": lane_name,
        "candidate_pool_size": pool_size,
        "max_length": config["lanes"][lane_name].get("max_length"),
        "query_count": len(candidates),
        "query_limit": config.get("query_limit"),
        "query_offset": config.get("query_offset", 0),
        "status": loaded.status,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_jsonl(model_dir / "reranked_results.jsonl", results)
    write_json(model_dir / "metrics.json", metrics)
    write_json(
        model_dir / "latency.json",
        {**latency, "samples_ms": timings},
    )
    write_json(model_dir / "manifest.json", manifest)
    return {
        "model": model_config["name"],
        "embedding_model": embedding_model,
        "lane": lane_name,
        "batch_size": model_config.get("batch_size"),
        "query_count": len(candidates),
        "candidate_pool_size": pool_size,
        "status": loaded.status,
        "metrics_path": str(model_dir / "metrics.json"),
        "latency_path": str(model_dir / "latency.json"),
        **metrics,
        **latency,
    }


def apply_candidate_pool_gates(
    rows: list[dict[str, Any]],
    gates: dict[str, Any],
) -> list[dict[str, Any]]:
    if not gates:
        return rows

    gated_rows = [dict(row) for row in rows]
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in gated_rows:
        if row.get("status") != "completed":
            continue
        pool_size = row.get("candidate_pool_size")
        if not isinstance(pool_size, int):
            continue
        key = (
            str(row.get("model", "")),
            str(row.get("embedding_model", "")),
            str(row.get("lane", "")),
        )
        groups.setdefault(key, []).append(row)

    quality_checks = (
        ("ndcg@10", "ndcg_at_10_max_drop"),
        ("mrr@10", "mrr_at_10_max_drop"),
        ("recall@10", "recall_at_10_max_drop"),
        ("hit@5", "hit_at_5_max_drop"),
    )
    min_improvement = float(gates.get("p95_min_improvement", 0.20))
    for group_rows in groups.values():
        reference = max(
            group_rows,
            key=lambda row: int(row["candidate_pool_size"]),
        )
        reference_p95 = float(reference["latency_p95_ms"])
        for row in group_rows:
            failures = []
            for metric_name, gate_name in quality_checks:
                drop = float(reference[metric_name]) - float(row[metric_name])
                row[f"{metric_name}_drop"] = drop
                if drop > float(gates[gate_name]) + 1e-12:
                    failures.append(f"{metric_name}_drop")

            row_p95 = float(row["latency_p95_ms"])
            improvement = (
                (reference_p95 - row_p95) / reference_p95
                if reference_p95 > 0
                else 0.0
            )
            row["latency_p95_improvement"] = improvement
            if row is reference:
                row["candidate_gate_status"] = "reference"
                row["candidate_gate_failures"] = []
                continue
            if improvement + 1e-12 < min_improvement:
                failures.append("p95_improvement")
            if row.get("latency_status") == "reject":
                failures.append("latency_hard_cap")
            row["candidate_gate_status"] = "reject" if failures else "pass"
            row["candidate_gate_failures"] = failures

    return gated_rows


def rerank_candidates(
    model: RerankerModel,
    records: list[dict[str, Any]],
    pool_size: int,
    *,
    progress_label: str | None = None,
) -> tuple[list[dict[str, Any]], list[float]]:
    output = []
    timings = []
    for index, record in enumerate(records, start=1):
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
        if progress_label:
            print(
                f"[{progress_label}] {index}/{len(records)} "
                f"{elapsed_ms:.1f} ms",
                flush=True,
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
    lines.extend(
        [
            "",
            "## Runs",
            "",
            "| Embedding | Reranker | Batch | Pool | NDCG@10 | MRR@10 | Recall@10 | Hit@5 | P95 ms | P95 improvement | Gate | Failures |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
        ]
    )
    for row in rows:
        failures = ", ".join(row.get("candidate_gate_failures", []))
        lines.append(
            "| {embedding} | {model} | {batch} | {pool} | {ndcg} | {mrr} | "
            "{recall} | {hit} | {p95} | {improvement} | {gate} | {failures} |".format(
                embedding=row.get("embedding_model", ""),
                model=row.get("model", ""),
                batch=row.get("batch_size", ""),
                pool=row.get("candidate_pool_size", ""),
                ndcg=row.get("ndcg@10", ""),
                mrr=row.get("mrr@10", ""),
                recall=row.get("recall@10", ""),
                hit=row.get("hit@5", ""),
                p95=row.get("latency_p95_ms", ""),
                improvement=row.get("latency_p95_improvement", ""),
                gate=row.get("candidate_gate_status", row.get("status", "")),
                failures=failures,
            )
        )
    lines.extend(["", "## Raw artifacts", ""])
    for row in rows:
        if row.get("metrics_path") and row.get("latency_path"):
            lines.append(
                f"- `{row.get('model')}` pool `{row.get('candidate_pool_size')}`: "
                f"`{row['metrics_path']}`; `{row['latency_path']}`"
            )
    lines.extend(
        [
            "",
            "## Config",
            "",
            f"- Dataset: `{config['dataset_version']}`",
            f"- Strategy: `{config['strategy_id']}`",
        ]
    )
    (run_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_registry(path: Path, run_dir: Path, rows: list[dict[str, Any]], config: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "component": "reranker",
        "task": "reranker_benchmark",
        "dataset_version": config["dataset_version"],
        "strategy_id": config["strategy_id"],
        "query_limit": config.get("query_limit"),
        "query_offset": config.get("query_offset", 0),
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
