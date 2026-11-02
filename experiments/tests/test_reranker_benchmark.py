import json
from pathlib import Path

import pytest
from experiments.src.reranker import benchmark as benchmark_module
from experiments.src.evaluation.metrics import mean_metrics
from experiments.src.reranker.benchmark import (
    group_candidates_by_embedding,
    rerank_candidates,
    run_model_lane,
    summarize_latency,
    write_skip,
)
from experiments.src.reranker.models import ModelLoadResult


def test_runtime_backend_adapter_passes_backend_length_and_batch(monkeypatch):
    from experiments.src.reranker import models

    calls = []

    class FakeRuntime:
        backend = "openvino"
        batch_size = 8

        def score_pairs(self, query, passages):
            calls.append((query, list(passages), self.batch_size))
            return [0.4 for _ in passages]

    fake = FakeRuntime()
    monkeypatch.setattr(
        "src.retrieval.reranking.load_reranker",
        lambda **kwargs: calls.append(kwargs) or fake,
    )

    loaded = models.load_reranker(
        {
            "name": "runtime-openvino-b16",
            "type": "runtime_backend",
            "backend": "openvino",
            "batch_size": 16,
        },
        {"max_length": 256},
        "cpu",
    )

    assert loaded.status == "completed"
    assert loaded.model.score_pairs("q", ["d"]) == [0.4]
    assert calls[0] == {
        "backend": "openvino",
        "device": "cpu",
        "max_length": 256,
    }
    assert calls[1] == ("q", ["d"], 16)


def test_runtime_backend_adapter_rejects_non_positive_batch(monkeypatch):
    from experiments.src.reranker import models

    calls = []
    monkeypatch.setattr(
        "src.retrieval.reranking.load_reranker",
        lambda **kwargs: calls.append(kwargs),
    )

    loaded = models.load_reranker(
        {
            "name": "runtime-openvino-invalid",
            "type": "runtime_backend",
            "backend": "openvino",
            "batch_size": 0,
        },
        {"max_length": 256},
        "cpu",
    )

    assert loaded.status == "skipped_model_load_failed"
    assert "batch_size" in (loaded.reason or "")
    assert calls == []

def test_runtime_benchmark_config_requires_candidate_source():
    from experiments.scripts.benchmark_runtime_reranker import build_config

    config_path = Path(
        "experiments/configs/reranker/runtime_openvino_ablation.yaml"
    )
    with pytest.raises(FileNotFoundError):
        build_config(config_path, Path("missing-candidates.jsonl"))


def test_runtime_benchmark_config_filters_candidate_pools(tmp_path):
    from experiments.scripts.benchmark_runtime_reranker import build_config

    candidate_source = tmp_path / "candidates.json"
    candidate_source.write_text("{}", encoding="utf-8")
    config = build_config(
        Path("experiments/configs/reranker/runtime_openvino_ablation.yaml"),
        candidate_source,
        pool_sizes=[40],
    )

    assert config["lanes"]["production"]["candidate_pool_sizes"] == [40]

class FakeReranker:
    name = "fake"
    def __init__(self):
        self.calls = 0


    def score_pairs(self, query, passages):
        self.calls += 1
        scores = []
        for passage in passages:
            if "best" in passage:
                scores.append(1.0)
            elif "tie" in passage:
                scores.append(0.5)
            else:
                scores.append(0.0)
        return scores


def test_rerank_candidates_sorts_by_score_then_original_rank():
    records = [
        {
            "query_id": "q1",
            "query": "question",
            "candidates": [
                {"doc_id": "d1", "rank": 1, "retrieval_score": 0.9, "text": "tie first", "metadata": {}},
                {"doc_id": "d2", "rank": 2, "retrieval_score": 0.8, "text": "best answer", "metadata": {}},
                {"doc_id": "d3", "rank": 3, "retrieval_score": 0.7, "text": "tie second", "metadata": {}},
            ],
        }
    ]

    results, timings = rerank_candidates(FakeReranker(), records, 3)

    assert timings[0] >= 0
    assert [item["doc_id"] for item in results[0]["results"]] == ["d2", "d1", "d3"]
    assert results[0]["results"][1]["original_rank"] == 1


def test_select_candidate_records_applies_offset_and_limit():
    records = [
        {"query_id": "q1"},
        {"query_id": "q2"},
        {"query_id": "q3"},
    ]

    selected = benchmark_module.select_candidate_records(
        records,
        offset=1,
        limit=1,
    )

    assert [record["query_id"] for record in selected] == ["q2"]


def test_required_runtime_benchmark_rejects_skipped_model():
    with pytest.raises(RuntimeError, match="runtime-openvino-b8"):
        benchmark_module.ensure_required_runs_completed(
            [
                {
                    "model": "runtime-openvino-b8",
                    "status": "skipped_model_load_failed",
                    "skip_reason": "missing runtime",
                }
            ]
        )


def test_mean_metrics_supports_precision_and_map():
    metrics = mean_metrics(
        {"q1": ["d2", "d1"], "q2": ["d3"]},
        {"q1": {"d1": 3}, "q2": {"d3": 3}},
        recall_at=[1, 2],
        mrr_at=[10],
        ndcg_at=[10],
        precision_at=[1],
        map_at=[10],
    )

    assert metrics["precision@1"] == 0.5
    assert metrics["recall@2"] == 1.0
    assert metrics["map@10"] == 0.75


def test_run_model_lane_includes_configured_hit_metric(tmp_path):
    candidates = [
        {
            "query_id": "q1",
            "query": "question",
            "embedding_model": "emb",
            "candidates": [
                {
                    "doc_id": "relevant",
                    "rank": 1,
                    "retrieval_score": 0.9,
                    "text": "best answer",
                    "metadata": {},
                }
            ],
        }
    ]
    config = {
        "metrics": {
            "recall_at": [1],
            "mrr_at": [1],
            "ndcg_at": [1],
            "precision_at": [1],
            "map_at": [1],
            "hit_at": [1],
        },
        "lanes": {"production": {"max_length": 256}},
        "latency_gates": {},
    }
    loaded = ModelLoadResult(
        name="fake",
        status="completed",
        model=FakeReranker(),
    )

    row = run_model_lane(
        tmp_path,
        config,
        {"name": "fake", "type": "fake"},
        loaded,
        "production",
        1,
        candidates,
        {"q1": {"relevant": 1}},
    )
    assert loaded.model.calls == 2

    assert row["hit@1"] == 1.0
    assert row["query_count"] == 1
    assert row["batch_size"] is None
    latency = json.loads(
        Path(row["latency_path"]).read_text(encoding="utf-8")
    )
    assert len(latency["samples_ms"]) == 1


def test_candidate_pool_gate_compares_with_same_model_largest_pool():
    rows = [
        {
            "model": "runtime-openvino-b8",
            "embedding_model": "emb",
            "lane": "production",
            "candidate_pool_size": 60,
            "status": "completed",
            "ndcg@10": 0.50,
            "mrr@10": 0.60,
            "recall@10": 0.70,
            "hit@5": 0.90,
            "latency_p95_ms": 100.0,
            "latency_status": "pass",
        },
        {
            "model": "runtime-openvino-b8",
            "embedding_model": "emb",
            "lane": "production",
            "candidate_pool_size": 32,
            "status": "completed",
            "ndcg@10": 0.497,
            "mrr@10": 0.595,
            "recall@10": 0.696,
            "hit@5": 0.90,
            "latency_p95_ms": 70.0,
            "latency_status": "pass",
        },
        {
            "model": "runtime-openvino-b8",
            "embedding_model": "emb",
            "lane": "production",
            "candidate_pool_size": 24,
            "status": "completed",
            "ndcg@10": 0.48,
            "mrr@10": 0.59,
            "recall@10": 0.69,
            "hit@5": 0.90,
            "latency_p95_ms": 90.0,
            "latency_status": "pass",
        },
    ]
    gates = {
        "ndcg_at_10_max_drop": 0.005,
        "mrr_at_10_max_drop": 0.010,
        "recall_at_10_max_drop": 0.005,
        "hit_at_5_max_drop": 0.005,
        "p95_min_improvement": 0.20,
    }

    gated = benchmark_module.apply_candidate_pool_gates(rows, gates)

    assert gated[0]["candidate_gate_status"] == "reference"
    assert gated[1]["candidate_gate_status"] == "pass"
    assert gated[1]["latency_p95_improvement"] == pytest.approx(0.30)
    assert gated[2]["candidate_gate_status"] == "reject"
    assert set(gated[2]["candidate_gate_failures"]) == {
        "ndcg@10_drop",
        "recall@10_drop",
        "p95_improvement",
    }


def test_latency_gate_classification():
    gates = {"demo_target_p95_ms": 800, "demo_hard_cap_p95_ms": 1500}

    assert summarize_latency([100, 200, 300], gates)["latency_status"] == "pass"
    assert summarize_latency([900, 1000, 1100], gates)["latency_status"] == "warn"
    assert summarize_latency([1600, 1700, 1800], gates)["latency_status"] == "reject"


def test_write_skip_records_reason(tmp_path):
    row = write_skip(tmp_path, {"name": "flashrank/test"}, "skipped_dependency_missing", "missing flashrank", "demo_safe")

    assert row["status"] == "skipped_dependency_missing"
    assert row["skip_reason"] == "missing flashrank"
    assert (tmp_path / "models" / "flashrank_test" / "demo_safe" / "skip.json").exists()


def test_group_candidates_by_embedding_keeps_sources_separate():
    grouped = group_candidates_by_embedding(
        [
            {"query_id": "q1", "embedding_model": "emb_a"},
            {"query_id": "q2", "embedding_model": "emb_b"},
            {"query_id": "q3", "embedding_model": "emb_a"},
        ]
    )

    assert [record["query_id"] for record in grouped["emb_a"]] == ["q1", "q3"]
    assert [record["query_id"] for record in grouped["emb_b"]] == ["q2"]
