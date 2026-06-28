from __future__ import annotations
import argparse
import json
import os
import sys
import time
from pathlib import Path
from torch.utils.data import DataLoader
from sentence_transformers import SentenceTransformer, InputExample, losses
from sentence_transformers.evaluation import InformationRetrievalEvaluator
from transformers.optimization import Adafactor

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.src.data.chunk_loader import load_chunks

def main():
    parser = argparse.ArgumentParser(description="Fine-tune embedding model (bge-m3) on synthetic queries.")
    parser.add_argument("--model-name", type=str, default="BAAI/bge-m3", help="Base model to fine-tune.")
    parser.add_argument("--epochs", type=int, default=1, help="Number of training epochs.")
    parser.add_argument("--batch-size", type=int, default=4, help="Batch size for training.")
    parser.add_argument("--eval-steps", type=int, default=500, help="Evaluate every N steps.")
    parser.add_argument("--lr", type=float, default=2e-5, help="Learning rate.")
    parser.add_argument("--use-cmnrl", action="store_true", help="Use Cached Multiple Negatives Ranking Loss.")
    parser.add_argument("--mini-batch-size", type=int, default=16, help="Mini batch size for Cached MNRL.")
    parser.add_argument("--freeze-layers", type=int, default=16, help="Number of layers to freeze (0 to 24).")
    parser.add_argument("--num-negatives", type=int, default=3, help="Number of hard negatives to use per query.")
    args = parser.parse_args()

    # Paths
    finetune_dir = ROOT / "experiments/data/finetune"
    train_file = finetune_dir / "train_queries.jsonl"
    train_hn_file = finetune_dir / "train_hard_negatives.jsonl"
    val_file = finetune_dir / "val_queries.jsonl"
    chunks_dir = ROOT / "experiments/data/chunks/recursive"
    
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    output_path = str(ROOT / f"experiments/runs/finetune/embedding/{timestamp}")

    print(f"=== Fine-tuning Embedding Model V3 ===")
    print(f"Base model: {args.model_name}")
    print(f"Epochs: {args.epochs}")
    print(f"Batch size: {args.batch_size}")
    print(f"Learning rate: {args.lr}")
    print(f"Use CMNRL: {args.use_cmnrl}")
    print(f"Mini batch size: {args.mini_batch_size}")
    print(f"Freeze layers: {args.freeze_layers}")
    print(f"Number of negatives: {args.num_negatives}")
    print(f"Output path: {output_path}")

    # 1. Load corpus chunks
    print("Loading corpus chunks...")
    chunks = load_chunks(chunks_dir, "recursive")
    corpus = {c["doc_id"]: c["text"] for c in chunks}
    print(f"Loaded {len(corpus)} corpus chunks.")

    # 2. Load train examples
    print("Loading training queries...")
    train_examples = []
    use_hard_negatives = False
    
    if train_hn_file.exists():
        print(f"Loading hard negatives from {train_hn_file}...")
        with open(train_hn_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    if "hard_negatives" in data and len(data["hard_negatives"]) > 0:
                        # texts format: [query, positive, negative_1, negative_2, ..., negative_N]
                        negatives = [neg["content"] for neg in data["hard_negatives"][:args.num_negatives]]
                        train_examples.append(InputExample(texts=[data["query"], data["pos_doc_content"]] + negatives))
                        use_hard_negatives = True
                    else:
                        train_examples.append(InputExample(texts=[data["query"], data["pos_doc_content"]]))
    else:
        print(f"No hard negatives file found. Loading training pairs from {train_file}...")
        with open(train_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    train_examples.append(InputExample(texts=[data["query"], data["pos_doc_content"]]))
    print(f"Loaded {len(train_examples)} training examples. Use hard negatives: {use_hard_negatives} (max {args.num_negatives} negatives/query)")

    # 3. Load validation / test evaluators
    print("Preparing evaluators...")
    
    # Validation Evaluator (Synthetic)
    val_queries = {}
    val_relevant_docs = {}
    with open(val_file, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if line.strip():
                data = json.loads(line)
                qid = f"val_q_{i}"
                val_queries[qid] = data["query"]
                val_relevant_docs[qid] = {data["pos_doc_id"]}
    
    val_evaluator = InformationRetrievalEvaluator(
        queries=val_queries,
        corpus=corpus,
        relevant_docs=val_relevant_docs,
        name="val_synthetic",
        mrr_at_k=[10],
        ndcg_at_k=[10],
        accuracy_at_k=[1, 5, 10],
        precision_recall_at_k=[1, 5, 10],
        show_progress_bar=False,
        batch_size=16
    )

    # Real Test Evaluator (Pilot Ground Truth)
    test_queries = {}
    test_queries_file = ROOT / "experiments/data/ground_truth/ground_truth_pilot.jsonl"
    with open(test_queries_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                test_queries[data["id"]] = data["question"]

    test_relevant_docs = {}
    qrels_file = ROOT / "experiments/data/processed/qrels_recursive.jsonl"
    with open(qrels_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                qid = data["query_id"]
                doc_id = data["doc_id"]
                if qid not in test_relevant_docs:
                    test_relevant_docs[qid] = set()
                test_relevant_docs[qid].add(doc_id)

    # Remove query ids that might not be in the queries file (just in case)
    test_relevant_docs = {qid: doc_ids for qid, doc_ids in test_relevant_docs.items() if qid in test_queries}

    test_evaluator = InformationRetrievalEvaluator(
        queries=test_queries,
        corpus=corpus,
        relevant_docs=test_relevant_docs,
        name="pilot_test",
        mrr_at_k=[10],
        ndcg_at_k=[10],
        accuracy_at_k=[1, 5, 10, 20, 40],
        precision_recall_at_k=[1, 5, 10, 20, 40],
        show_progress_bar=False,
        batch_size=16
    )

    import torch
    torch.cuda.empty_cache()
    
    print(f"Loading base model '{args.model_name}'...")
    model = SentenceTransformer(args.model_name)
    model.max_seq_length = 384
    
    # Freeze embeddings and the first N layers of the encoder to save memory
    trainable_before = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    
    auto_model = model[0].auto_model
    for param in auto_model.embeddings.parameters():
        param.requires_grad = False
    
    # Freeze up to args.freeze_layers layers (there are 24 layers in BGE-M3's XLM-RoBERTa-large encoder)
    num_frozen = min(max(0, args.freeze_layers), 24)
    for i in range(num_frozen):
        for param in auto_model.encoder.layer[i].parameters():
            param.requires_grad = False
            
    trainable_after = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Layer Freezing: Frozen first {num_frozen} encoder layers. Trainable parameters reduced from {trainable_before:,} to {trainable_after:,} ({(trainable_after / total_params) * 100:.1f}% trainable)")
    print(f"Model loaded on device: {model.device}, max_seq_length set to {model.max_seq_length}")

    # 5. Train
    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=args.batch_size)
    
    if args.use_cmnrl:
        print(f"Using CachedMultipleNegativesRankingLoss with mini_batch_size={args.mini_batch_size}...")
        train_loss = losses.CachedMultipleNegativesRankingLoss(model=model, mini_batch_size=args.mini_batch_size)
    else:
        print("Using standard MultipleNegativesRankingLoss...")
        train_loss = losses.MultipleNegativesRankingLoss(model=model)

    print("Starting fine-tuning...")
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        evaluator=None,
        epochs=args.epochs,
        output_path=output_path,
        save_best_model=False,
        optimizer_class=Adafactor,
        optimizer_params={"lr": args.lr, "scale_parameter": False, "relative_step": False, "warmup_init": False},
        use_amp=True,
        warmup_steps=int(len(train_dataloader) * 0.1)
    )
    print(f"Training completed. Saving final model to: {output_path}")
    model.save(output_path)

if __name__ == "__main__":
    main()
