# Corrected-query OpenVINO candidate matrix (20 queries)

Runtime: OpenVINO `2026.4.0`, PyTorch CPU `2.12.0`, Transformers `4.57.6`, Tokenizers `0.22.2`; corrected tokenizer regex enabled. Latency is cold-inclusive per-query scoring and excludes model load.

| Batch | Pool | NDCG@10 | MRR@10 | Recall@10 | Hit@5 | Mean ms | P50 ms | P95 ms | Improvement | Gate | Failures |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| 8 | 24 | 0.461146 | 0.764583 | 0.381806 | 0.850000 | 7809.6 | 7815.0 | 8018.0 | 59.7% | pass |  |
| 8 | 32 | 0.462636 | 0.760417 | 0.390139 | 0.850000 | 11007.3 | 10875.4 | 12399.2 | 37.8% | pass |  |
| 8 | 40 | 0.459756 | 0.764583 | 0.380139 | 0.850000 | 13579.5 | 13318.3 | 15594.8 | 21.7% | reject | recall@10_drop, latency_hard_cap |
| 8 | 48 | 0.459077 | 0.763889 | 0.380139 | 0.850000 | 13178.8 | 13145.1 | 13823.1 | 30.6% | reject | recall@10_drop |
| 8 | 60 | 0.458454 | 0.763889 | 0.386389 | 0.850000 | 16299.3 | 16147.4 | 19919.4 | 0.0% | reference |  |
| 16 | 24 | 0.439051 | 0.739583 | 0.374583 | 0.850000 | 7577.4 | 7593.2 | 8166.5 |  | reject_batch_parity | batch_size_changes_ranking_metrics |
| 16 | 32 | 0.437656 | 0.727976 | 0.374583 | 0.850000 | 9396.7 | 8968.8 | 11669.6 |  | reject_batch_parity | batch_size_changes_ranking_metrics |
