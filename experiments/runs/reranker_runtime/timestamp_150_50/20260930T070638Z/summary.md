# Reranker Benchmark Summary

## Candidate Metrics

- `query_count`: 20
- `sources`: {'bge_m3-finetuned-v3': {'query_count': 20, 'no_qrels_query_count': 0, 'recall@10': 0.51, 'recall_new@10': 0.51, 'recall@40': 0.7116666666666667, 'recall_new@40': 0.7116666666666667, 'mrr@10': 0.6808333333333334, 'ndcg@10': 0.49919783425180747, 'precision@1': 0.55, 'map@10': 0.34843882275132276}}
- `benchmark_query_offset`: 10
- `benchmark_query_count`: 10

## Runs

| Embedding | Reranker | Batch | Pool | NDCG@10 | MRR@10 | Recall@10 | Hit@5 | P95 ms | P95 improvement | Gate | Failures |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| bge_m3-finetuned-v3 | runtime-openvino-b8 | 8 | 40 | 0.5399795802683193 | 0.8333333333333334 | 0.4525 | 0.9 | 15330.567299993709 | 0.0 | reference |  |

## Raw artifacts

- `runtime-openvino-b8` pool `40`: `C:\uit_HK5\CS431\final_project\experiments\runs\reranker_runtime\timestamp_150_50\20260930T070638Z\models\runtime_openvino_b8\bge_m3_finetuned_v3\production\top_40\metrics.json`; `C:\uit_HK5\CS431\final_project\experiments\runs\reranker_runtime\timestamp_150_50\20260930T070638Z\models\runtime_openvino_b8\bge_m3_finetuned_v3\production\top_40\latency.json`

## Config

- Dataset: `runtime_openvino_ablation_v1`
- Strategy: `timestamp_150_50`
