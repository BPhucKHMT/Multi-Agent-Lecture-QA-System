# Reranker Benchmark Summary

## Candidate Metrics

- `query_count`: 20
- `sources`: {'bge_m3-finetuned-v3': {'query_count': 20, 'no_qrels_query_count': 0, 'recall@10': 0.51, 'recall_new@10': 0.51, 'recall@40': 0.7116666666666667, 'recall_new@40': 0.7116666666666667, 'mrr@10': 0.6808333333333334, 'ndcg@10': 0.49919783425180747, 'precision@1': 0.55, 'map@10': 0.34843882275132276}}

## Runs

| Embedding | Reranker | Batch | Pool | NDCG@10 | MRR@10 | Recall@10 | Hit@5 | P95 ms | P95 improvement | Gate | Failures |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| bge_m3-finetuned-v3 | runtime-openvino-b8 | 8 | 32 | 0.46263562606761327 | 0.7604166666666667 | 0.3901388888888889 | 0.85 | 12399.229574995115 | 0.0 | reference |  |

## Raw artifacts

- `runtime-openvino-b8` pool `32`: `C:\uit_HK5\CS431\final_project\experiments\runs\reranker_runtime\timestamp_150_50\20260930T065648Z\models\runtime_openvino_b8\bge_m3_finetuned_v3\production\top_32\metrics.json`; `C:\uit_HK5\CS431\final_project\experiments\runs\reranker_runtime\timestamp_150_50\20260930T065648Z\models\runtime_openvino_b8\bge_m3_finetuned_v3\production\top_32\latency.json`

## Config

- Dataset: `runtime_openvino_ablation_v1`
- Strategy: `timestamp_150_50`
