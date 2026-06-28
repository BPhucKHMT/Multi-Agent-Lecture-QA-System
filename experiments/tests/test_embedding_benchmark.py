import json
from pathlib import Path

from experiments.src.benchmark.embedding_benchmark import run_embedding_benchmark, stable_hash


class FakeEmbedder:
    name = "fake-model"

    def encode(self, texts):
        vectors = []
        for text in texts:
            vectors.append([1.0, 0.0] if "alpha" in text else [0.0, 1.0])
        return vectors


def test_run_embedding_benchmark_reads_reusable_index_and_writes_run_outputs(tmp_path: Path, monkeypatch):
    index_dir = tmp_path / "indexes" / "chroma" / "recursive" / "fake-model"
    index_dir.mkdir(parents=True)
    query_path = tmp_path / "queries.jsonl"
    qrels_path = tmp_path / "qrels.jsonl"
    query_path.write_text(json.dumps({"id": "q1", "question": "alpha question", "category": "definition"}) + "\n", encoding="utf-8")
    qrels_path.write_text(json.dumps({"query_id": "q1", "doc_id": "v1_0_30", "relevance": 3}) + "\n", encoding="utf-8")

    def fake_query_chroma_index(queries, index_dir, collection_name, embedder, top_k):
        assert str(index_dir).endswith("fake-model")
        assert collection_name == "idx-recursive-fake-model"
        assert top_k == 2
        return (
            {"q1": ["v1_0_30", "v2_0_30"]},
            [{"query_id": "q1", "question": "alpha question", "results": [{"rank": 1, "doc_id": "v1_0_30", "score": 1.0}]}],
            {"retrieval_backend": "chroma", "index_path": str(index_dir), "collection_name": collection_name},
        )

    monkeypatch.setattr("experiments.src.benchmark.embedding_benchmark.query_chroma_index", fake_query_chroma_index)

    config = {
        "dataset_version": "unit",
        "strategy_id": "recursive",
        "index_dir": str(index_dir),
        "collection_name": "idx-recursive-fake-model",
        "query_path": str(query_path),
        "qrels_path": str(qrels_path),
        "run_root": str(tmp_path / "runs" / "embedding"),
        "registry_path": str(tmp_path / "runs" / "registry.jsonl"),
        "top_k": 2,
        "retrieval_backend": "chroma",
        "metrics": {"recall_at": [1, 10], "mrr_at": [10], "ndcg_at": [10]},
        "model": {"name": "fake-model"},
    }

    run_dir = run_embedding_benchmark(config=config, embedder=FakeEmbedder(), limit=1)

    assert run_dir.parent.name == "fake-model"
    assert run_dir.parent.parent.name == "recursive"
    assert (run_dir / "eval_results.json").exists()
    assert (run_dir / "metrics.json").exists()
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "config.yaml").exists()
    assert not (run_dir / "chroma").exists()
    assert not (run_dir / "chroma_langchain_mmr").exists()

    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["recall@1"] == 1.0
    assert metrics["mrr@10"] == 1.0

    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["split"] == "test"
    assert manifest["retrieval_backend"] == "chroma"
    assert manifest["index_dir"] == str(index_dir)
    assert manifest["index_path"] == str(index_dir)
    assert manifest["collection_name"] == "idx-recursive-fake-model"
    assert "chunks_dir" not in manifest
    assert len(manifest["config_hash"]) == 12
    assert manifest["config_hash"] == stable_hash({**config, "run_root": "ignored", "registry_path": "ignored"})

    registry_lines = (tmp_path / "runs" / "registry.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(registry_lines) == 1
    registry_entry = json.loads(registry_lines[0])
    assert registry_entry["status"] == "completed"
    assert registry_entry["split"] == "test"
    assert registry_entry["top_k"] == 2
    assert registry_entry["query_count"] == 1
    assert "chunk_count" not in registry_entry
    assert registry_entry["retrieval_backend"] == "chroma"
    assert registry_entry["index_path"] == str(index_dir)
    assert registry_entry["collection_name"] == "idx-recursive-fake-model"
    assert registry_entry["primary_metric"] == "recall@10"
    assert registry_entry["primary_metric_value"] == 1.0
    assert registry_entry["metrics_path"].endswith("metrics.json")


def test_run_embedding_benchmark_rejects_missing_index_dir(tmp_path: Path):
    query_path = tmp_path / "queries.jsonl"
    qrels_path = tmp_path / "qrels.jsonl"
    query_path.write_text(json.dumps({"id": "q1", "question": "alpha question"}) + "\n", encoding="utf-8")
    qrels_path.write_text(json.dumps({"query_id": "q1", "doc_id": "v1_0_30", "relevance": 3}) + "\n", encoding="utf-8")

    missing_index_dir = tmp_path / "indexes" / "missing"
    config = {
        "dataset_version": "unit",
        "strategy_id": "recursive",
        "index_dir": str(missing_index_dir),
        "collection_name": "idx-recursive-fake-model",
        "query_path": str(query_path),
        "qrels_path": str(qrels_path),
        "run_root": str(tmp_path / "runs"),
        "registry_path": str(tmp_path / "registry.jsonl"),
        "retrieval_backend": "chroma",
        "model": {"name": "fake-model"},
    }

    try:
        run_embedding_benchmark(config=config, embedder=FakeEmbedder(), limit=1)
    except FileNotFoundError as error:
        assert "Reusable index_dir does not exist" in str(error)
    else:
        raise AssertionError("Expected FileNotFoundError")


def test_run_embedding_benchmark_rejects_non_reusable_backend(tmp_path: Path):
    query_path = tmp_path / "queries.jsonl"
    qrels_path = tmp_path / "qrels.jsonl"
    query_path.write_text(json.dumps({"id": "q1", "question": "alpha question"}) + "\n", encoding="utf-8")
    qrels_path.write_text(json.dumps({"query_id": "q1", "doc_id": "v1_0_30", "relevance": 3}) + "\n", encoding="utf-8")

    config = {
        "dataset_version": "unit",
        "strategy_id": "recursive",
        "index_dir": str(tmp_path / "index"),
        "collection_name": "idx-recursive-fake-model",
        "query_path": str(query_path),
        "qrels_path": str(qrels_path),
        "run_root": str(tmp_path / "runs"),
        "registry_path": str(tmp_path / "registry.jsonl"),
        "retrieval_backend": "langchain_chroma_mmr",
        "model": {"name": "fake-model"},
    }

    try:
        run_embedding_benchmark(config=config, embedder=FakeEmbedder(), limit=1)
    except ValueError as error:
        assert "Unsupported reusable index backend" in str(error)
    else:
        raise AssertionError("Expected ValueError")
