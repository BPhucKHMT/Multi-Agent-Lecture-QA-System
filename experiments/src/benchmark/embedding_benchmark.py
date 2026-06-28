import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple, Union

from experiments.src.data.qrels_loader import load_qrels
from experiments.src.evaluation.metrics import mean_metrics
from experiments.src.indexing.chroma_index import query_chroma_index


class Embedder(Protocol):
    name: str

    def encode(self, texts: list[str]) -> list[list[float]]:
        ...


def run_embedding_benchmark(config: Dict[str, Any], embedder: Embedder, limit: Optional[int] = None) -> Path:
    strategy_id = config["strategy_id"]
    model_name = config["model"]["name"]
    config_hash = stable_hash(config)
    run_dir = build_run_dir(Path(config["run_root"]), strategy_id, model_name, config_hash)
    run_id = run_dir.name
    run_dir.mkdir(parents=True, exist_ok=True)

    queries = load_queries(Path(config["query_path"]), limit)
    qrels = load_qrels(config["qrels_path"])
    rankings, eval_results, index_info = retrieve(
        queries,
        embedder,
        int(config.get("top_k", 10)),
        config,
        run_dir=run_dir,
    )

    metric_config = config.get("metrics", {})
    metrics = mean_metrics(
        rankings,
        qrels,
        recall_at=metric_config.get("recall_at", [5, 10]),
        mrr_at=metric_config.get("mrr_at", [10]),
        ndcg_at=metric_config.get("ndcg_at", [10]),
        precision_at=metric_config.get("precision_at"),
        map_at=metric_config.get("map_at"),
        hit_at=metric_config.get("hit_at", [5, 10]),
        aliases=metric_config.get("aliases"),
    )
    manifest = build_manifest(config, run_id, config_hash, run_dir, len(queries), index_info)

    write_json(run_dir / "eval_results.json", eval_results)
    write_json(run_dir / "metrics.json", metrics)
    write_json(run_dir / "manifest.json", manifest)
    write_config_copy(config, run_dir / "config.yaml")
    append_registry(Path(config["registry_path"]), manifest, metrics, run_dir)
    return run_dir


def load_queries(path: Path, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    queries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("category") == "no_answer":
            continue
        queries.append({"query_id": record["id"], "text": record["question"], "category": record.get("category", "")})
        if limit and len(queries) >= limit:
            break
    return queries


def retrieve(
    queries: list[dict[str, Any]],
    embedder: Embedder,
    top_k: int,
    config: Dict[str, Any],
    run_dir: Optional[Path] = None,
) -> Tuple[Dict[str, List[str]], List[Dict[str, Any]], Dict[str, Any]]:
    backend = config.get("retrieval_backend", "chroma")
    if backend == "langchain_chroma_mmr":
        if "chunks_dir" not in config:
            raise ValueError(f"Unsupported reusable index backend: {backend}")
        if not run_dir:
            raise ValueError("run_dir is required for langchain_chroma_mmr backend")
        index_dir = run_dir / "chroma_langchain_mmr"
        model_name = config["model"]["name"].lower().replace("/", "-").replace("_", "-")
        collection_name = f"emb-{config['strategy_id']}-{model_name}"[:50].strip("-")
        
        from experiments.src.indexing.chroma_index import build_chroma_index
        build_chroma_index({
            "chunks_dir": config["chunks_dir"],
            "strategy_id": config["strategy_id"],
            "dataset_version": config["dataset_version"],
            "index_dir": str(index_dir),
            "collection_name": collection_name,
            "model": config["model"],
        }, embedder)
        
        from langchain_chroma import Chroma
        class LangchainEmbeddingsWrapper:
            def __init__(self, embedder):
                self.embedder = embedder
            def embed_documents(self, texts):
                return self.embedder.encode(texts)
            def embed_query(self, text):
                return self.embedder.encode([text])[0]
                
        db = Chroma(
            persist_directory=str(index_dir),
            embedding_function=LangchainEmbeddingsWrapper(embedder),
            collection_name=collection_name,
        )
        search_kwargs = config.get("search_kwargs", {"k": top_k, "fetch_k": 80, "lambda_mult": 0.7})
        retriever = db.as_retriever(
            search_type="mmr",
            search_kwargs=search_kwargs,
        )
        
        rankings: dict[str, list[str]] = {}
        eval_results: list[dict[str, Any]] = []
        for query in queries:
            docs = retriever.invoke(query["text"])
            rankings[query["query_id"]] = [doc.metadata["doc_id"] for doc in docs]
            eval_results.append({
                "query_id": query["query_id"],
                "question": query["text"],
                "results": [
                    {
                        "rank": idx + 1,
                        "doc_id": doc.metadata["doc_id"],
                        "score": 1.0,
                        "video_id": doc.metadata.get("filename"),
                        "video_url": doc.metadata.get("video_url"),
                        "start_timestamp": doc.metadata.get("start_timestamp"),
                        "end_timestamp": doc.metadata.get("end_timestamp"),
                    }
                    for idx, doc in enumerate(docs)
                ],
            })
            
        return rankings, eval_results, {
            "retrieval_backend": "langchain_chroma_mmr",
            "index_path": str(index_dir),
            "collection_name": collection_name,
            "search_type": "mmr",
            "search_kwargs": search_kwargs,
        }

    if backend != "chroma":
        raise ValueError(f"Unsupported reusable index backend: {backend}")
    if "index_dir" not in config:
        if not run_dir:
            raise ValueError("run_dir is required for chroma backend without reusable index")
        index_dir = run_dir / "chroma"
        model_name = config["model"]["name"].lower().replace("/", "-").replace("_", "-")
        collection_name = f"emb-{config['strategy_id']}-{model_name}"[:50].strip("-")
        
        from experiments.src.indexing.chroma_index import build_chroma_index
        build_chroma_index({
            "chunks_dir": config["chunks_dir"],
            "strategy_id": config["strategy_id"],
            "dataset_version": config["dataset_version"],
            "index_dir": str(index_dir),
            "collection_name": collection_name,
            "model": config["model"],
        }, embedder)
        
        return query_chroma_index(
            queries=queries,
            index_dir=index_dir,
            collection_name=collection_name,
            embedder=embedder,
            top_k=top_k,
        )

    index_dir = Path(config["index_dir"])
    if not index_dir.exists():
        raise FileNotFoundError(f"Reusable index_dir does not exist: {index_dir}")
    return query_chroma_index(
        queries=queries,
        index_dir=index_dir,
        collection_name=config["collection_name"],
        embedder=embedder,
        top_k=top_k,
    )


def build_chroma_results(ids: list[str], distances: list[float], metadatas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for rank, (_, distance, metadata) in enumerate(zip(ids, distances, metadatas, strict=True), start=1):
        results.append(
            {
                "rank": rank,
                "doc_id": metadata["doc_id"],
                "score": 1.0 - distance,
                "video_id": metadata.get("filename"),
                "video_url": metadata.get("video_url"),
                "start_timestamp": metadata.get("start_timestamp"),
                "end_timestamp": metadata.get("end_timestamp"),
            }
        )
    return results


def to_chroma_metadata(chunk: Dict[str, Any]) -> Dict[str, Union[str, int, float, bool]]:
    metadata = {"doc_id": chunk["doc_id"]}
    for key, value in chunk["metadata"].items():
        if isinstance(value, (str, int, float, bool)):
            metadata[key] = value
    return metadata


def build_manifest(
    config: Dict[str, Any],
    run_id: str,
    config_hash: str,
    run_dir: Path,
    query_count: int,
    index_info: dict[str, Any],
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "component": "embedding",
        "task": "rag_retrieval_benchmark",
        "strategy_id": config["strategy_id"],
        "model": config["model"]["name"],
        "dataset_version": config["dataset_version"],
        "config_hash": config_hash,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "split": config.get("split", "test"),
        "query_count": query_count,
        "top_k": config.get("top_k", 10),
        "index_dir": config.get("index_dir"),
        "query_path": config["query_path"],
        "qrels_path": config["qrels_path"],
        "run_dir": str(run_dir),
        "metrics_path": str(run_dir / "metrics.json"),
        **index_info,
    }


def append_registry(path: Path, manifest: dict[str, Any], metrics: dict[str, Any], run_dir: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    primary_metric = choose_primary_metric(metrics)
    entry = {
        "run_id": manifest["run_id"],
        "component": manifest["component"],
        "task": manifest["task"],
        "strategy_id": manifest["strategy_id"],
        "model": manifest["model"],
        "dataset_version": manifest["dataset_version"],
        "split": manifest["split"],
        "top_k": manifest["top_k"],
        "query_count": manifest["query_count"],
        "retrieval_backend": manifest["retrieval_backend"],
        "index_path": manifest.get("index_path"),
        "collection_name": manifest.get("collection_name"),
        "status": "completed",
        "config_hash": manifest["config_hash"],
        "primary_metric": primary_metric,
        "primary_metric_value": metrics.get(primary_metric),
        "run_dir": str(run_dir),
        "metrics_path": str(run_dir / "metrics.json"),
        "created_at": manifest["created_at"],
    }
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")


def stable_hash(config: dict[str, Any]) -> str:
    payload = json.dumps(logical_config(config), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def logical_config(config: dict[str, Any]) -> dict[str, Any]:
    ignored = {"__config_path", "run_root", "registry_path"}
    return {key: value for key, value in config.items() if key not in ignored}


def build_run_dir(run_root: Path, strategy_id: str, model_name: str, config_hash: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return run_root / strategy_id / slugify(model_name) / f"{timestamp}_{config_hash}"


def slugify(value: str) -> str:
    return value.lower().replace("/", "-").replace("_", "-")


def choose_primary_metric(metrics: dict[str, Any]) -> str:
    recall_metrics = [key for key in metrics if key.startswith("recall@")]
    if recall_metrics:
        return sorted(recall_metrics, key=lambda key: int(key.split("@")[1]))[-1]
    return next((key for key in metrics if key not in {"query_count", "no_qrels_query_count"}), "query_count")


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def write_config_copy(config: dict[str, Any], path: Path) -> None:
    source_path = config.get("__config_path")
    if source_path and Path(source_path).exists():
        shutil.copy2(source_path, path)
        return
    write_json(path, config)
