from experiments.src.evaluation.metrics import mean_metrics
from experiments.src.reranker.benchmark import group_candidates_by_embedding, rerank_candidates, summarize_latency, write_skip


class FakeReranker:
    name = "fake"

    def score_pairs(self, query, passages):
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
