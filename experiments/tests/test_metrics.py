from experiments.src.evaluation.metrics import mean_metrics


def test_mean_metrics_computes_recall_mrr_and_ndcg():
    rankings = {
        "q1": ["d3", "d1", "d2"],
        "q2": ["d4", "d5"],
        "q_no_answer": ["d9"],
    }
    qrels = {
        "q1": {"d1": 3, "d2": 1},
        "q2": {"d5": 2},
    }

    metrics = mean_metrics(rankings, qrels, recall_at=[1, 2], mrr_at=[2], ndcg_at=[2])

    assert metrics["query_count"] == 2
    assert metrics["no_qrels_query_count"] == 1
    assert metrics["recall@1"] == 0.0
    assert metrics["recall@2"] == 0.75
    assert metrics["mrr@2"] == 0.5
    assert round(metrics["ndcg@2"], 4) == 0.6048


def test_mean_metrics_handles_empty_qrels_without_crash():
    metrics = mean_metrics({"q1": ["d1"]}, {}, recall_at=[10], mrr_at=[10], ndcg_at=[10])

    assert metrics["query_count"] == 0
    assert metrics["no_qrels_query_count"] == 1
    assert metrics["recall@10"] == 0.0
    assert metrics["mrr@10"] == 0.0
    assert metrics["ndcg@10"] == 0.0


def test_mean_metrics_counts_duplicate_ranked_doc_once():
    rankings = {"q1": ["d1", "d1", "d2"]}
    qrels = {"q1": {"d1": 1, "d2": 1}}

    metrics = mean_metrics(
        rankings,
        qrels,
        recall_at=[3],
        mrr_at=[3],
        ndcg_at=[3],
        precision_at=[3],
        map_at=[3],
    )

    assert metrics["recall@3"] == 1.0
    assert metrics["precision@3"] == 2 / 3
    assert metrics["map@3"] == 1.0
    assert metrics["mrr@3"] == 1.0
    assert metrics["ndcg@3"] == 1.0


class EmptyButTruthyQrels:
    def __len__(self):
        return 0

    def __bool__(self):
        return True

    def __contains__(self, doc_id):
        return False

    def get(self, doc_id, default=0):
        return default

    def values(self):
        return []


def test_mean_metrics_skips_truthy_qrels_with_zero_relevant_docs():
    metrics = mean_metrics(
        {"q1": ["d1"]},
        {"q1": EmptyButTruthyQrels()},
        recall_at=[10],
        mrr_at=[10],
        ndcg_at=[10],
    )

    assert metrics["query_count"] == 0
    assert metrics["no_qrels_query_count"] == 1
    assert metrics["recall@10"] == 0.0


def test_mean_metrics_computes_recall_new(monkeypatch):
    mock_evidence = {
        "q1": [("vid1", 100, 200), ("vid1", 300, 400)],
        "q2": [("vid2", 50, 150)],
    }
    monkeypatch.setattr(
        "experiments.src.evaluation.metrics._load_evidence_queries",
        lambda: mock_evidence
    )

    rankings = {
        "q1": ["vid1_150_250", "vid1_500_600"],
        "q2": ["vid2_200_300"],
    }
    qrels = {
        "q1": {"vid1_150_250": 1},
        "q2": {"vid2_200_300": 1},
    }

    metrics = mean_metrics(
        rankings,
        qrels,
        recall_at=[2],
        mrr_at=[2],
        ndcg_at=[2],
        recall_new_at=[2],
    )

    assert metrics["recall_new@2"] == 0.25

