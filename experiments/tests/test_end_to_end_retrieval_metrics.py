from experiments.src.evaluation.metrics import mean_metrics


def test_mean_metrics_computes_hit_at_k_aliases():
    rankings = {
        "q1": ["d0", "d1"],
        "q2": ["d2", "d3"],
        "q3": ["d9"],
    }
    qrels = {
        "q1": {"d1": 1},
        "q2": {"d8": 1},
        "q3": {"d9": 1},
    }

    metrics = mean_metrics(rankings, qrels, recall_at=[1, 2], mrr_at=[2], ndcg_at=[2], hit_at=[1, 2])

    assert metrics["hit@1"] == 1 / 3
    assert metrics["hit@2"] == 2 / 3


def test_mean_metrics_can_emit_candidate_and_final_metric_names():
    rankings = {
        "q1": ["d1", "d2"],
        "q2": ["d4"],
    }
    qrels = {
        "q1": {"d2": 1},
        "q2": {"d5": 1},
    }

    metrics = mean_metrics(
        rankings,
        qrels,
        recall_at=[10, 40],
        mrr_at=[10],
        ndcg_at=[10],
        hit_at=[5],
        aliases={
            "candidate_hit@40": "hit@40",
            "candidate_recall@40": "recall@40",
            "final_hit@5": "hit@5",
            "final_recall@10": "recall@10",
        },
    )

    assert metrics["candidate_hit@40"] == 0.5
    assert metrics["candidate_recall@40"] == 0.5
    assert metrics["final_hit@5"] == 0.5
    assert metrics["final_recall@10"] == 0.5
