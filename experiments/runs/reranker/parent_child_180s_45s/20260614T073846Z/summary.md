# Reranker Benchmark Summary

## Candidate Metrics

- `query_count`: 2
- `sources`: {'BAAI/bge-m3': {'query_count': 2, 'no_qrels_query_count': 0, 'recall@1': 0.0, 'recall@5': 0.125, 'recall@10': 0.2159090909090909, 'recall@20': 0.3693181818181818, 'recall@40': 0.3693181818181818, 'mrr@10': 0.3333333333333333, 'ndcg@5': 0.1917831836856678, 'ndcg@10': 0.22841665073603223, 'precision@1': 0.0, 'map@10': 0.09553571428571428}}

## Runs

| Embedding | Reranker | Pool | Status | NDCG@10 | MRR@10 | Recall@40 | P95 ms | Latency |
|---|---|---:|---|---:|---:|---:|---:|---|
| BAAI/bge-m3 | no_rerank | 10 | completed | 0.22841665073603223 | 0.3333333333333333 | 0.2159090909090909 | 0.013515044702216983 | pass |
| BAAI/bge-m3 | no_rerank | 40 | completed | 0.22841665073603223 | 0.3333333333333333 | 0.3693181818181818 | 0.011285030632279813 | pass |

## Config

- Dataset: `phase4_parent_child_v1`
- Strategy: `parent_child_180s_45s`
