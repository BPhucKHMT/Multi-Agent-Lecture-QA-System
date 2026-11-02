# Reranker Benchmark Summary

## Candidate Metrics

- `query_count`: 10
- `sources`: {'bge_m3-finetuned-v3': {'query_count': 10, 'no_qrels_query_count': 0, 'recall@10': 0.49333333333333335, 'recall_new@10': 0.49333333333333335, 'recall@40': 0.7133333333333333, 'recall_new@40': 0.7133333333333333, 'mrr@10': 0.6583333333333333, 'ndcg@10': 0.49790431333041624, 'precision@1': 0.5, 'map@10': 0.35708994708994707}}
- `benchmark_query_offset`: 0
- `benchmark_query_count`: 10

## Runs

| Embedding | Reranker | Batch | Pool | NDCG@10 | MRR@10 | Recall@10 | Hit@5 | P95 ms | P95 improvement | Gate | Failures |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| bge_m3-finetuned-v3 | runtime-openvino-b8 | 8 | 60 | 0.37652546199597914 | 0.6944444444444444 | 0.3077777777777778 | 0.8 | 17252.656780031975 | 0.0 | reference |  |

## Raw artifacts

- `runtime-openvino-b8` pool `60`: `C:\uit_HK5\CS431\final_project\experiments\runs\reranker_runtime\timestamp_150_50\20260930T071602Z\models\runtime_openvino_b8\bge_m3_finetuned_v3\production\top_60\metrics.json`; `C:\uit_HK5\CS431\final_project\experiments\runs\reranker_runtime\timestamp_150_50\20260930T071602Z\models\runtime_openvino_b8\bge_m3_finetuned_v3\production\top_60\latency.json`

## Config

- Dataset: `runtime_openvino_ablation_v1`
- Strategy: `timestamp_150_50`
