import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.scripts.embedding_factory import create_embedder
from experiments.scripts.benchmark_embeddings import load_config, resolve_paths as resolve_dense_paths
from experiments.scripts.benchmark_hybrid_retrieval import resolve_paths as resolve_hybrid_paths
from experiments.src.benchmark.embedding_benchmark import run_embedding_benchmark
from experiments.src.benchmark.hybrid_retrieval import run_hybrid_benchmark
from experiments.src.data.chunk_loader import load_chunks, load_parent_chunks
from experiments.src.data.qrels_loader import load_dynamic_qrels, load_parent_qrels_from_child_qrels
from experiments.src.evaluation.metrics import mean_metrics
from experiments.src.reranker.models import load_reranker
from experiments.src.reranker.parent_child_adapter import adapt_parent_child_candidates

CONFIGS = [
    ("C01", "dense", "experiments/configs/embedding/recursive_bge_m3.yaml"),
    ("C02", "hybrid", "experiments/configs/embedding/recursive_bge_m3_hybrid.yaml"),
    ("C03", "dense", "experiments/configs/embedding/recursive_halong_embedding.yaml"),
    ("C04", "hybrid", "experiments/configs/embedding/recursive_halong_embedding_hybrid.yaml"),
    ("C05", "dense", "experiments/configs/embedding/timestamp_90_30_bge_m3.yaml"),
    ("C06", "hybrid", "experiments/configs/embedding/timestamp_90_30_bge_m3_hybrid.yaml"),
    ("C07", "dense", "experiments/configs/embedding/timestamp_90_30_halong_embedding.yaml"),
    ("C08", "hybrid", "experiments/configs/embedding/timestamp_90_30_halong_embedding_hybrid.yaml"),
    ("C09", "dense", "experiments/configs/embedding/parent_child_180s_45s_bge_m3_child.yaml"),
    ("C10", "hybrid", "experiments/configs/embedding/parent_child_180s_45s_bge_m3_child_hybrid.yaml"),
    ("C11", "dense", "experiments/configs/embedding/parent_child_180s_45s_halong_embedding_child.yaml"),
    ("C12", "hybrid", "experiments/configs/embedding/parent_child_180s_45s_halong_embedding_child_hybrid.yaml"),
    ("C13", "dense", "experiments/configs/embedding/recursive_bge_m3_finetuned_v2.yaml"),
    ("C14", "hybrid", "experiments/configs/embedding/recursive_bge_m3_finetuned_v2_hybrid.yaml"),
    ("C15", "dense", "experiments/configs/embedding/recursive_bge_m3_finetuned_v3.yaml"),
    ("C16", "hybrid", "experiments/configs/embedding/recursive_bge_m3_finetuned_v3_hybrid.yaml"),
    ("C17", "dense", "experiments/configs/embedding/timestamp_90_30_bge_m3_finetuned_v3.yaml"),
    ("C18", "hybrid", "experiments/configs/embedding/timestamp_90_30_bge_m3_finetuned_v3_hybrid.yaml"),
    ("C19", "hybrid", "experiments/configs/embedding/semantic_bge_m3_finetuned_v3_hybrid.yaml"),
    ("C20", "hybrid", "experiments/configs/embedding/semantic_openai_text_embedding_3_large_hybrid.yaml"),
    ("C21", "hybrid", "experiments/configs/embedding/timestamp_150_50_bge_m3_finetuned_v3_hybrid.yaml"),
    ("C22", "hybrid", "experiments/configs/embedding/parent_child_180s_45s_bge_m3_finetuned_v3_child_hybrid.yaml"),
    ("C23", "dense", "experiments/configs/embedding/timestamp_150_50_bge_m3_finetuned_v3.yaml"),
    ("C24", "hybrid", "experiments/configs/embedding/timestamp_150_50_bge_m3_hybrid.yaml"),
    ("C25", "dense", "experiments/configs/embedding/timestamp_150_50_bge_m3.yaml"),
    ("C21_norerank", "hybrid", "experiments/configs/embedding/timestamp_150_50_bge_m3_finetuned_v3_hybrid.yaml"),
]

JINA_CONFIG = {
    "name": "jinaai/jina-reranker-v2-base-multilingual",
    "type": "sentence_transformers_cross_encoder",
    "batch_size": 128,
    "trust_remote_code": True,
}
LANE_CONFIG = {"max_length": 1024, "candidate_pool_sizes": [40]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run 12 E2E retrieval configs with Jina rerank.")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--query-path", type=str, default="experiments/data/ground_truth/ground_truth_pilot.jsonl",
                        help="Path to the query file relative to ROOT")
    parser.add_argument("--configs", type=str, help="Comma-separated config IDs to run, e.g. C15,C16")
    args = parser.parse_args()

    target_configs = [c.strip() for c in args.configs.split(",")] if args.configs else None

    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    reranker = load_reranker(JINA_CONFIG, LANE_CONFIG, device)
    if reranker.model is None:
        raise RuntimeError(reranker.reason or "Jina reranker load failed")

    summary_path = ROOT / "experiments/runs/e2e_summary/end_to_end_12_config_results.json"
    existing_summary = []
    if summary_path.exists():
        try:
            existing_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    summary_dict = {row["config_id"]: row for row in existing_summary}

    for config_id, retrieval_type, config_path in CONFIGS:
        if target_configs and config_id not in target_configs:
            continue
        config = load_config(ROOT / config_path)
        config = resolve_hybrid_paths(config) if retrieval_type == "hybrid" else resolve_dense_paths(config)
        if args.query_path:
            config["query_path"] = str((ROOT / args.query_path).resolve())
        print(f"[{config_id}] retrieval={retrieval_type} strategy={config['strategy_id']} model={config['model']['name']}")
        retrieval_dir = run_retrieval(config, retrieval_type, args.limit)
        if config_id.endswith("_norerank"):
            row = run_jina_rerank(config_id, retrieval_type, config, retrieval_dir, None)
        else:
            row = run_jina_rerank(config_id, retrieval_type, config, retrieval_dir, reranker.model)
        summary_dict[config_id] = row
        print(format_row(row))

    sorted_summary = [summary_dict[k] for k in sorted(summary_dict.keys())]
    write_summary(sorted_summary)



def run_retrieval(config: dict[str, Any], retrieval_type: str, limit: int | None) -> Path:
    import gc
    import torch
    model_config = config["model"]
    run_config = copy.deepcopy(config)
    run_config["run_root"] = str(Path(config["run_root"]).parent / "e2e_retrieval" / retrieval_type)
    embedder = create_embedder(model_config)
    runner = run_hybrid_benchmark if retrieval_type == "hybrid" else run_embedding_benchmark
    res_dir = runner(run_config, embedder, limit=limit)

    # Free embedder VRAM to prevent GPU memory leak
    if hasattr(embedder, "model"):
        del embedder.model
    del embedder
    gc.collect()
    torch.cuda.empty_cache()

    return res_dir


def run_jina_rerank(config_id: str, retrieval_type: str, config: dict[str, Any], retrieval_dir: Path, reranker: Any) -> dict[str, Any]:
    eval_results = json.loads((retrieval_dir / "eval_results.json").read_text(encoding="utf-8"))
    chunks = load_chunks(config["chunks_dir"], strategy_id=config["strategy_id"])
    chunk_by_id = {chunk["doc_id"]: chunk for chunk in chunks}
    parent_by_id = {chunk["doc_id"]: chunk for chunk in load_parent_chunks(config["chunks_dir"])} if config["strategy_id"] == "parent_child_180s_45s" else {}
    qrels = load_parent_qrels_from_child_qrels(config["qrels_path"], chunks) if config["strategy_id"] == "parent_child_180s_45s" else load_dynamic_qrels(config["query_path"], chunks)

    reranked_records = []
    rankings = {}
    for record in eval_results:
        candidates = build_candidates(record, config, chunk_by_id, parent_by_id)
        selected = candidates[:40]
        if reranker is not None:
            scores = reranker.score_pairs(record["question"], [candidate["text"] for candidate in selected])
            reranked = [{**candidate, "reranker_score": float(score)} for candidate, score in zip(selected, scores, strict=True)]
            reranked.sort(key=lambda item: (-item["reranker_score"], item["rank"]))
        else:
            reranked = [{**candidate, "reranker_score": 0.0} for candidate in selected]
        results = [to_result(rank, item) for rank, item in enumerate(reranked, start=1)]
        reranked_records.append({"query_id": record["query_id"], "question": record["question"], "results": results})
        rankings[record["query_id"]] = [item["doc_id"] for item in results]

    metrics = mean_metrics(
        rankings,
        qrels,
        recall_at=[5, 10, 40],
        mrr_at=[10],
        ndcg_at=[10],
        hit_at=[1, 5, 10, 40],
        recall_new_at=[10, 40],
    )
    out_dir = Path(config["run_root"]).parent / "e2e_reranked" / config_id
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "metrics.json", metrics)
    write_json(out_dir / "reranked_results.json", reranked_records)
    return {
        "config_id": config_id,
        "retrieval": retrieval_type,
        "strategy_id": config["strategy_id"],
        "embedding": config["model"]["name"],
        "query_count": len(reranked_records),
        "retrieval_dir": str(retrieval_dir),
        "rerank_dir": str(out_dir),
        **metrics,
    }


def build_candidates(record: dict[str, Any], config: dict[str, Any], chunk_by_id: dict[str, Any], parent_by_id: dict[str, Any]) -> list[dict[str, Any]]:
    if config["strategy_id"] == "parent_child_180s_45s":
        return adapt_parent_child_candidates(record["results"], chunk_by_id, parent_by_id)
    candidates = []
    for row in record["results"][:40]:
        chunk = chunk_by_id.get(row["doc_id"])
        if not chunk:
            continue
        candidates.append({"doc_id": row["doc_id"], "rank": int(row["rank"]), "retrieval_score": float(row.get("score", 0.0)), "text": chunk["text"], "metadata": chunk["metadata"]})
    return candidates


def to_result(rank: int, item: dict[str, Any]) -> dict[str, Any]:
    return {"rank": rank, "doc_id": item["doc_id"], "original_rank": item["rank"], "retrieval_score": item["retrieval_score"], "reranker_score": item["reranker_score"]}


def write_summary(rows: list[dict[str, Any]]) -> None:
    out_dir = ROOT / "experiments/runs/e2e_summary"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "end_to_end_12_config_results.json", rows)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def format_row(row: dict[str, Any]) -> str:
    return f"{row['config_id']} Hit@5={row.get('hit@5')} Recall@40={row.get('recall@40')} MRR@10={row.get('mrr@10')} NDCG@10={row.get('ndcg@10')}"


if __name__ == "__main__":
    main()
