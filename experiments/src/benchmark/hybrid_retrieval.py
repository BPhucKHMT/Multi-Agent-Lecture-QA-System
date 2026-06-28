import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

from experiments.src.benchmark.embedding_benchmark import (
    append_registry,
    build_manifest,
    load_queries,
    stable_hash,
    write_config_copy,
    write_json,
)
from experiments.src.data.chunk_loader import load_chunks
from experiments.src.data.qrels_loader import load_qrels
from experiments.src.evaluation.metrics import mean_metrics
from experiments.src.indexing.chroma_index import query_chroma_index


class Embedder(Protocol):
    name: str

    def encode(self, texts: list[str]) -> list[list[float]]:
        ...


def run_hybrid_benchmark(config: Dict[str, Any], embedder: Embedder, limit: Optional[int] = None) -> Path:
    strategy_id = config["strategy_id"]
    model_name = config["model"]["name"]
    config_hash = stable_hash(config)
    run_dir = build_hybrid_run_dir(Path(config["run_root"]), strategy_id, model_name, config_hash)
    run_id = run_dir.name
    run_dir.mkdir(parents=True, exist_ok=True)

    top_k = int(config.get("top_k", 40))
    queries = load_queries(Path(config["query_path"]), limit)
    qrels = load_qrels(config["qrels_path"])
    rankings, eval_results, retrieval_info = retrieve_hybrid(queries, embedder, top_k, config)

    metric_config = config.get("metrics", {})
    metrics = mean_metrics(
        rankings,
        qrels,
        recall_at=metric_config.get("recall_at", [10, 40]),
        mrr_at=metric_config.get("mrr_at", [10]),
        ndcg_at=metric_config.get("ndcg_at", [10]),
        precision_at=metric_config.get("precision_at", []),
        map_at=metric_config.get("map_at", []),
        hit_at=metric_config.get("hit_at", [5, 40]),
        aliases=metric_config.get("aliases"),
    )
    manifest = build_manifest(config, run_id, config_hash, run_dir, len(queries), retrieval_info)
    manifest["component"] = "hybrid_retrieval"

    write_json(run_dir / "eval_results.json", eval_results)
    write_json(run_dir / "metrics.json", metrics)
    write_json(run_dir / "manifest.json", manifest)
    write_config_copy(config, run_dir / "config.yaml")
    append_registry(Path(config["registry_path"]), manifest, metrics, run_dir)
    return run_dir


def retrieve_hybrid(
    queries: list[dict[str, Any]],
    embedder: Embedder,
    top_k: int,
    config: dict[str, Any],
) -> tuple[dict[str, list[str]], list[dict[str, Any]], dict[str, Any]]:
    dense_rankings, dense_results, dense_info = query_chroma_index(
        queries=queries,
        index_dir=config["index_dir"],
        collection_name=config["collection_name"],
        embedder=embedder,
        top_k=top_k,
    )
    chunks = load_chunks(config["chunks_dir"], strategy_id=config["strategy_id"])
    bm25_rankings = BM25Index(chunks).rank_many(queries, top_k=top_k)
    dense_by_query = {row["query_id"]: row["results"] for row in dense_results}

    rankings: dict[str, list[str]] = {}
    eval_results: list[dict[str, Any]] = []
    for query in queries:
        query_id = query["query_id"]
        fused = weighted_rrf(
            [dense_rankings.get(query_id, []), bm25_rankings.get(query_id, [])],
            weights=config.get("hybrid_weights", [0.5, 0.5]),
            top_k=top_k,
        )
        rankings[query_id] = [doc_id for doc_id, _ in fused]
        eval_results.append(
            {
                "query_id": query_id,
                "question": query["text"],
                "results": build_hybrid_results(fused, dense_by_query.get(query_id, [])),
            }
        )

    return rankings, eval_results, {
        "retrieval_backend": "hybrid_0_5_0_5",
        "dense_backend": dense_info.get("retrieval_backend", "chroma"),
        "bm25_field": "page_content + OCR",
        "hybrid_weights": config.get("hybrid_weights", [0.5, 0.5]),
        "index_path": str(config["index_dir"]),
        "collection_name": config["collection_name"],
    }


def build_hybrid_results(fused: list[tuple[str, float]], dense_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dense_metadata = {row["doc_id"]: row for row in dense_rows}
    results = []
    for rank, (doc_id, score) in enumerate(fused, start=1):
        row = dict(dense_metadata.get(doc_id, {}))
        row.update({"rank": rank, "doc_id": doc_id, "score": score})
        results.append(row)
    return results


def weighted_rrf(rankings: list[list[str]], weights: list[float], top_k: int, k: int = 60) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranking, weight in zip(rankings, weights, strict=True):
        seen: set[str] = set()
        for rank, doc_id in enumerate(ranking, start=1):
            if doc_id in seen:
                continue
            seen.add(doc_id)
            scores[doc_id] = scores.get(doc_id, 0.0) + weight / (k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:top_k]


class BM25Index:
    def __init__(self, chunks: list[dict[str, Any]], k1: float = 1.5, b: float = 0.75) -> None:
        self.doc_ids = [chunk["doc_id"] for chunk in chunks]
        self.documents = [enriched_text(chunk) for chunk in chunks]
        self.k1 = k1
        self.b = b
        self.term_frequencies = [Counter(tokenize(document)) for document in self.documents]
        self.doc_lengths = [sum(counter.values()) for counter in self.term_frequencies]
        self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths) if self.doc_lengths else 0.0
        self.doc_frequency = Counter()
        for counter in self.term_frequencies:
            self.doc_frequency.update(counter.keys())
        self.doc_count = len(self.documents)

    def rank_many(self, queries: list[dict[str, Any]], top_k: int) -> dict[str, list[str]]:
        return {query["query_id"]: self.rank(query["text"], top_k) for query in queries}

    def rank(self, query: str, top_k: int) -> list[str]:
        query_terms = tokenize(query)
        scores = []
        for index, counter in enumerate(self.term_frequencies):
            score = self.score(query_terms, counter, self.doc_lengths[index])
            if score > 0:
                scores.append((self.doc_ids[index], score))
        return [doc_id for doc_id, _ in sorted(scores, key=lambda item: (-item[1], item[0]))[:top_k]]

    def score(self, query_terms: list[str], counter: Counter[str], doc_length: int) -> float:
        score = 0.0
        for term in query_terms:
            term_frequency = counter.get(term, 0)
            if term_frequency == 0:
                continue
            idf = math.log(1 + (self.doc_count - self.doc_frequency[term] + 0.5) / (self.doc_frequency[term] + 0.5))
            denominator = term_frequency + self.k1 * (1 - self.b + self.b * doc_length / self.avg_doc_length)
            score += idf * term_frequency * (self.k1 + 1) / denominator
        return score


def enriched_text(chunk: dict[str, Any]) -> str:
    ocr_text = chunk.get("metadata", {}).get("ocr_content") or ""
    return f"{chunk.get('text', '')}\n[OCR Context]: {ocr_text}"


def tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)


def build_hybrid_run_dir(run_root: Path, strategy_id: str, model_name: str, config_hash: str) -> Path:
    from experiments.src.benchmark.embedding_benchmark import slugify
    from datetime import datetime, timezone

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return run_root / "hybrid_0_5_0_5" / strategy_id / slugify(model_name) / f"{timestamp}_{config_hash}"
