import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple

from experiments.src.benchmark.embedding_benchmark import retrieve, stable_hash
from experiments.src.data.chunk_loader import load_chunks, load_parent_chunks
from experiments.src.data.qrels_loader import load_dynamic_qrels, load_parent_qrels_from_child_qrels
from experiments.src.evaluation.metrics import mean_metrics
from experiments.src.reranker.parent_child_adapter import adapt_parent_child_candidates


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str, batch_size: int = 16, normalize_embeddings: bool = True) -> None:
        from sentence_transformers import SentenceTransformer

        self.name = model_name
        self.batch_size = batch_size
        self.normalize_embeddings = normalize_embeddings
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=self.normalize_embeddings,
            show_progress_bar=True,
        )
        return embeddings.tolist()


def load_queries(path: Union[str, Path], limit: Optional[int] = None) -> List[Dict[str, Any]]:
    queries = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("category") == "no_answer":
            continue
        queries.append({"query_id": record["id"], "text": record["question"], "category": record.get("category", "")})
        if limit and len(queries) >= limit:
            break
    return queries


def build_candidates(config: Dict[str, Any], run_dir: Path, limit: Optional[int] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    chunks = load_chunks(config["chunks_dir"], strategy_id=config["strategy_id"])
    chunk_by_id = {chunk["doc_id"]: chunk for chunk in chunks}
    parent_by_id = load_parent_chunk_map(config) if config["strategy_id"] == "parent_child_180s_45s" else {}
    qrels = load_strategy_qrels(config, chunks)
    candidate_sources = config.get("candidate_sources") or [{"name": config["retriever"]["embedding_model"], "path": config.get("candidate_source_path")}]
    all_records = []
    source_metrics = {}
    for source in candidate_sources:
        records, metrics = build_candidate_source(config, run_dir, limit, chunk_by_id, qrels, source, parent_by_id)
        all_records.extend(records)
        source_metrics[source["name"]] = metrics
    candidate_metrics = {"query_count": len(all_records), "sources": source_metrics}
    write_json(run_dir / "candidate_metrics.json", candidate_metrics)
    return all_records, candidate_metrics


def build_candidate_source(
    config: Dict[str, Any],
    run_dir: Path,
    limit: Optional[int],
    chunk_by_id: Dict[str, Any],
    qrels: Dict[str, Dict[str, int]],
    source: Dict[str, Any],
    parent_by_id: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    candidate_source = source.get("path")
    candidate_dir = run_dir / "candidate_index"
    if candidate_source:
        eval_results = json.loads(Path(candidate_source).read_text(encoding="utf-8"))
        if limit:
            eval_results = eval_results[:limit]
        index_info = {"retrieval_backend": "precomputed", "candidate_source_path": str(candidate_source), "embedding_model": source["name"]}
    else:
        queries = load_queries(config["query_path"], limit)
        retriever_config = build_retriever_config(config)
        embedder = SentenceTransformerEmbedder(
            source["name"],
            batch_size=int(config["retriever"].get("batch_size", 16)),
            normalize_embeddings=bool(config["retriever"].get("normalize_embeddings", True)),
        )
        _, eval_results, index_info = retrieve(
            queries=queries,
            embedder=embedder,
            top_k=int(config["candidate_top_n"]),
            config=retriever_config,
        )
    records = []
    rankings = {}
    for result in eval_results:
        if config["strategy_id"] == "parent_child_180s_45s":
            candidates = adapt_parent_child_candidates(
                rows=result["results"][: int(config["candidate_top_n"] )],
                child_by_id=chunk_by_id,
                parent_by_id=parent_by_id or {},
            )
        else:
            candidates = []
            for row in result["results"][: int(config["candidate_top_n"] )]:
                chunk = chunk_by_id.get(row["doc_id"])
                if not chunk:
                    continue
                candidates.append(
                    {
                        "doc_id": row["doc_id"],
                        "rank": int(row["rank"]),
                        "retrieval_score": float(row.get("score", 0.0)),
                        "text": chunk["text"],
                        "metadata": chunk["metadata"],
                    }
                )
        records.append(
            {
                "query_id": result["query_id"],
                "query": result["question"],
                "embedding_model": source["name"],
                "candidate_pool_size": len(candidates),
                "candidates": candidates,
            }
        )
        rankings[result["query_id"]] = [candidate["doc_id"] for candidate in candidates]
    metric_config = config.get("metrics", {})
    candidate_metrics = mean_metrics(
        rankings,
        qrels,
        recall_at=metric_config.get("recall_at", [10, 20, 50, 100]),
        mrr_at=metric_config.get("mrr_at", [10]),
        ndcg_at=metric_config.get("ndcg_at", [10]),
        precision_at=metric_config.get("precision_at", [1]),
        map_at=metric_config.get("map_at", [10]),
    )
    manifest = {
        "component": "reranker",
        "task": "candidate_generation",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "query_count": len(records),
        "chunk_count": len(chunk_by_id),
        "candidate_top_n": config["candidate_top_n"],
        "retriever": config["retriever"],
        "index_info": index_info,
    }
    source_dir = run_dir / "candidates" / slugify(source["name"])
    write_jsonl(source_dir / "candidates.jsonl", records)
    write_json(source_dir / "candidate_metrics.json", candidate_metrics)
    write_json(source_dir / "candidate_manifest.json", manifest)
    if candidate_dir.exists():
        shutil.rmtree(candidate_dir, ignore_errors=True)
    return records, candidate_metrics


def slugify(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value).strip("_").lower()


def build_retriever_config(config: dict[str, Any]) -> dict[str, Any]:
    retriever = config["retriever"]
    return {
        "dataset_version": config["dataset_version"],
        "strategy_id": config["strategy_id"],
        "chunks_dir": config["chunks_dir"],
        "query_path": config["query_path"],
        "qrels_path": config["qrels_path"],
        "run_root": str(Path(config["run_root"]) / "candidate_index"),
        "registry_path": config["registry_path"],
        "top_k": config["candidate_top_n"],
        "retrieval_backend": retriever.get("retrieval_backend", "chroma"),
        "index_dir": config["index_dir"],
        "collection_name": config["collection_name"],
        "model": {
            "name": retriever["embedding_model"],
            "batch_size": retriever.get("batch_size", 16),
            "normalize_embeddings": retriever.get("normalize_embeddings", True),
        },
    }


def load_strategy_qrels(config: dict[str, Any], chunks: list[dict[str, Any]]) -> dict[str, Any]:
    if config["strategy_id"] == "parent_child_180s_45s":
        return load_parent_qrels_from_child_qrels(config["qrels_path"], chunks)
    return load_dynamic_qrels(config["query_path"], chunks)


def load_parent_chunk_map(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {chunk["doc_id"]: chunk for chunk in load_parent_chunks(config["chunks_dir"])}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n", encoding="utf-8")
