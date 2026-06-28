# experiments — Benchmark & Evaluation

`experiments/` chứa toàn bộ pipeline benchmark, evaluation và fine-tuning cho retrieval pipeline của PUQ Q&A. Mục tiêu: chọn cấu hình chunking + embedding + reranker tối ưu cho RAG lecture QA tiếng Việt.

---

## Cấu trúc thư mục chi tiết

```txt
experiments/
├── __init__.py
├── configs/
│   ├── .gitkeep
│   ├── embedding/
│   │   ├── benchmark.yaml
│   │   ├── parent_child_180s_45s_bge_m3_child.yaml
│   │   ├── parent_child_180s_45s_bge_m3_child_hybrid.yaml
│   │   ├── parent_child_180s_45s_bge_m3_finetuned_v3_child_hybrid.yaml
│   │   ├── parent_child_180s_45s_halong_embedding_child.yaml
│   │   ├── parent_child_180s_45s_halong_embedding_child_hybrid.yaml
│   │   ├── recursive/
│   │   │   ├── bge_m3_test_top10.yaml
│   │   │   ├── bge_m3_test_top100.yaml
│   │   │   ├── bkai_vietnamese_bi_encoder_test_top100.yaml
│   │   │   ├── dangvantuan_vietnamese_embedding_test_top100.yaml
│   │   │   ├── multilingual_e5_large_test_top100.yaml
│   │   │   ├── production_mmr.yaml
│   │   │   ├── scenario1_raw_similarity.yaml
│   │   │   ├── scenario2_mmr.yaml
│   │   │   ├── recursive_bge_m3.yaml
│   │   │   ├── recursive_bge_m3_finetuned.yaml
│   │   │   ├── recursive_bge_m3_finetuned_v2.yaml
│   │   │   ├── recursive_bge_m3_finetuned_v2_hybrid.yaml
│   │   │   ├── recursive_bge_m3_finetuned_v3.yaml
│   │   │   ├── recursive_bge_m3_finetuned_v3_hybrid.yaml
│   │   │   ├── recursive_bge_m3_hybrid.yaml
│   │   │   ├── recursive_halong_embedding.yaml
│   │   │   ├── recursive_halong_embedding_hybrid.yaml
│   │   │   ├── recursive_multilingual_e5_large.yaml
│   │   │   └── recursive_multilingual_e5_large_hybrid.yaml
│   │   ├── recursive_bge_m3_hybrid.yaml
│   │   ├── recursive_bge_m3_finetuned_v2_hybrid.yaml
│   │   ├── recursive_bge_m3_finetuned_v3_hybrid.yaml
│   │   ├── recursive_halong_embedding_hybrid.yaml
│   │   ├── recursive_multilingual_e5_large_hybrid.yaml
│   │   ├── timestamp_90_30_bge_m3_hybrid.yaml
│   │   ├── timestamp_90_30_halong_embedding_hybrid.yaml
│   │   ├── timestamp_90_30_bge_m3.yaml
│   │   ├── timestamp_90_30_halong_embedding.yaml
│   │   ├── timestamp_150_50_bge_m3_ft_v3.yaml
│   │   └── timestamp_150_50_bge_m3_ft_v3_hybrid.yaml
│   └── index/
│       ├── parent_child_180s_45s_bge_m3_child.yaml
│       ├── parent_child_180s_45s_halong_embedding_child.yaml
│       ├── recursive_bge_m3.yaml
│       ├── recursive_halong_embedding.yaml
│       ├── timestamp_90_30_bge_m3.yaml
│       ├── timestamp_90_30_halong_embedding.yaml
│       └── timestamp_150_50_bge_m3_ft_v3.yaml
├── docs/
│   ├── data/
│   │   └── groundtruth.md          # Hướng dẫn tạo ground truth dataset (350 câu hỏi)
│   └── evaluation/
│       ├── end_to_end_retrieval.md # 22-config retrieval benchmark (MAIN)
│       ├── embedding.md            # So sánh 7 embedding models
│       ├── reranker.md             # So sánh 6 reranker models
│       ├── qa_metrics.md           # QA quality: BERTScore + RAGAS
│       └── bge_m3_loss_curve.png   # Training loss curve
├── indexes/                        # ChromaDB indexes đã build (gitignored)
├── runs/
│   ├── e2e_reranked/               # End-to-end retrieval + rerank results
│   ├── e2e_retrieval/              # Retrieval-only results
│   ├── embedding/                  # Embedding benchmark outputs
│   ├── finetune/
│   │   ├── embedding/              # Fine-tuned embedding outputs
│   │   └── reranker/               # Fine-tuned reranker outputs
│   ├── hybrid/                     # Hybrid search benchmark outputs
│   ├── qa_metrics/                 # QA quality predictions (JSONL)
│   │   ├── qa_metrics_report.md
│   │   ├── C02_predictions.jsonl
│   │   ├── C19_predictions.jsonl
│   │   ├── C21_predictions.jsonl
│   │   └── C22_predictions.jsonl
│   └── reranker/                   # Reranker benchmark outputs
├── scripts/
│   ├── benchmark_embeddings.py          # Run embedding benchmark
│   ├── benchmark_end_to_end_retrieval.py # Run full E2E retrieval benchmark
│   ├── benchmark_hybrid_retrieval.py    # Run hybrid search benchmark
│   ├── benchmark_qa_metrics.py          # Run QA quality (BERTScore + RAGAS)
│   ├── benchmark_rerankers.py           # Run reranker benchmark
│   ├── build_index.py                   # Build ChromaDB index từ config
│   ├── build_manifests.py               # Build chunk manifests
│   ├── embedding_factory.py             # Factory cho embedding models
│   ├── finetune_embedding.py            # Fine-tune embedding model
│   ├── finetune_reranker.py             # Fine-tune reranker model
│   ├── generate_parent_child_chunks.py  # Generate parent-child chunks
│   ├── generate_qrels.py                # Generate qrels từ ground truth
│   ├── generate_semantic_chunks.py      # Generate semantic chunks
│   ├── generate_synthetic_queries.py    # Generate synthetic queries cho GT
│   ├── generate_timestamp_90_30_chunks.py # Generate timestamp 90_30 chunks
│   ├── prepare_chunk_strategy.py        # Prepare chunk strategy config
│   ├── normalize_groundtruth.py         # Normalize ground truth JSONL
│   ├── train_splits.py                  # Train/test split cho fine-tune
│   ├── augment_queries.py               # Augment queries cho fine-tune
│   ├── audit_reranker_failures.py       # Audit reranker failures
│   ├── audit_synthetic_queries.py       # Audit synthetic query quality
│   ├── estimate_openai_embedding_cost.py # Estimate OpenAI embedding cost
│   ├── estimate_semantic_chunking_openai_cost.py # Estimate semantic chunking cost
│   ├── mine_hard_negatives.py           # Mine hard negatives cho fine-tune
│   └── create_semantic_qrels.py         # Create qrels cho semantic chunks
├── src/
│   ├── __init__.py
│   ├── time_utils.py
│   ├── benchmark/
│   │   ├── embedding_benchmark.py  # Embedding benchmark runner
│   │   └── hybrid_retrieval.py     # Hybrid retrieval benchmark runner
│   ├── data/
│   │   ├── loaders.py              # Data loaders
│   │   └── ...
│   ├── evaluation/
│   │   ├── metrics.py              # Hit@K, Recall, MRR, NDCG
│   │   └── ...
│   ├── indexing/
│   │   └── ...                     # ChromaDB index builders
│   ├── qrels/
│   │   └── ...                     # Qrels processing
│   └── reranker/
│       └── ...                     # Reranker evaluation
├── tests/
│   ├── test_audit_reranker_failures.py
│   ├── test_chroma_index.py
│   ├── test_embedding_benchmark.py
│   ├── test_end_to_end_retrieval_metrics.py
│   ├── test_hybrid_retrieval.py
│   ├── test_loaders.py
│   ├── test_metrics.py
│   ├── test_parent_child_adapter.py
│   ├── test_parent_child_chunks.py
│   ├── test_parent_child_loader.py
│   ├── test_parent_child_qrels.py
│   ├── test_qa_metrics.py
│   ├── test_qrels_overlap.py
│   └── test_reranker_benchmark.py
└── scratch/                         # Thử nghiệm nhanh, throwaway
```

---

## Cài đặt

```powershell
pip install -r requirements.txt
pip install -r requirements.pipeline.txt   # nếu cần fine-tune
```

---

## Benchmark nhanh

### 1. Build ChromaDB index

```powershell
python experiments/scripts/build_index.py --config experiments/configs/index/<config>.yaml
```

Ví dụ:

```powershell
python experiments/scripts/build_index.py --config experiments/configs/index/timestamp_150_50_bge_m3_ft_v3.yaml
```

### 2. Chạy end-to-end retrieval benchmark

```powershell
python experiments/scripts/benchmark_end_to_end_retrieval.py
```

Output: `experiments/runs/e2e_reranked/<timestamp>/`

### 3. Chạy embedding benchmark

```powershell
python experiments/scripts/benchmark_embeddings.py --config experiments/configs/embedding/<config>.yaml
```

### 4. Chạy reranker benchmark

```powershell
python experiments/scripts/benchmark_rerankers.py
```

### 5. Chạy QA quality benchmark (BERTScore + RAGAS)

```powershell
python experiments/scripts/benchmark_qa_metrics.py
```

Output: `experiments/runs/qa_metrics/`

---

## Kết quả benchmark chính

### Winner: C21 — Hybrid + Timestamp 150_50 Raw + BGE-M3 FT v3 + Jina Reranker

| Metric | C21 | C02 (runner-up) |
|---|---:|---:|
| Hit@1 | 0.7067 | 0.6500 |
| Hit@5 | **0.9467** | 0.8967 |
| Recall@40 | 0.7758 | **0.7954** |
| MRR@10 | **0.8085** | 0.7471 |
| NDCG@10 | **0.6092** | 0.5205 |

Chi tiết đầy đủ 22 configs: [docs/evaluation/end_to_end_retrieval.md](docs/evaluation/end_to_end_retrieval.md)

---

## Ground truth dataset

Tạo ground truth 350 câu hỏi cho evaluation:

```powershell
# Xem hướng dẫn
cat experiments/docs/data/groundtruth.md

# Generate synthetic queries
python experiments/scripts/generate_synthetic_queries.py --config <config>.yaml

# Normalize ground truth
python experiments/scripts/normalize_groundtruth.py --input <raw.jsonl> --output <normalized.jsonl>

# Generate qrels từ ground truth
python experiments/scripts/generate_qrels.py --config <config>.yaml
```

---

## Fine-tuning

### Fine-tune embedding model

```powershell
python experiments/scripts/finetune_embedding.py --config experiments/configs/embedding/<config>.yaml
```

Output: `experiments/runs/finetune/embedding/<timestamp>/`

### Fine-tune reranker

```powershell
python experiments/scripts/finetune_reranker.py --config <config>.yaml
```

Output: `experiments/runs/finetune/reranker/<timestamp>/`

---

## Unit tests

```powershell
python -m pytest experiments/tests/
```

---

## Liên kết tài liệu

| Document | Nội dung |
|---|---|
| [docs/evaluation/end_to_end_retrieval.md](docs/evaluation/end_to_end_retrieval.md) | 22-config retrieval benchmark, winner analysis |
| [docs/evaluation/embedding.md](docs/evaluation/embedding.md) | So sánh 7 embedding models |
| [docs/evaluation/reranker.md](docs/evaluation/reranker.md) | So sánh 6 reranker models |
| [docs/evaluation/qa_metrics.md](docs/evaluation/qa_metrics.md) | QA quality: BERTScore + RAGAS |
| [docs/data/groundtruth.md](docs/data/groundtruth.md) | Hướng dẫn tạo ground truth dataset |
