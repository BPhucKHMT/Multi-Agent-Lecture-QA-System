from __future__ import annotations
import argparse
import json
import os
import sys
import time
from pathlib import Path
from torch.utils.data import DataLoader
from sentence_transformers import CrossEncoder, InputExample
from sentence_transformers.cross_encoder.evaluation import CrossEncoderRerankingEvaluator
from transformers.optimization import Adafactor

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

def main():
    parser = argparse.ArgumentParser(description="Fine-tune CrossEncoder (Jina Reranker) on synthetic queries with hard negatives.")
    parser.add_argument("--model-name", type=str, default="jinaai/jina-reranker-v2-base-multilingual", help="Base model to fine-tune.")
    parser.add_argument("--epochs", type=int, default=1, help="Number of training epochs.")
    parser.add_argument("--batch-size", type=int, default=4, help="Batch size for training.")
    parser.add_argument("--eval-steps", type=int, default=500, help="Evaluate every N steps.")
    parser.add_argument("--lr", type=float, default=2e-5, help="Learning rate.")
    args = parser.parse_args()

    # Paths
    finetune_dir = ROOT / "experiments/data/finetune"
    train_file = finetune_dir / "train_hard_negatives.jsonl"
    val_file = finetune_dir / "val_hard_negatives.jsonl"
    
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    output_path = str(ROOT / f"experiments/runs/finetune/reranker/{timestamp}")

    print(f"=== Fine-tuning CrossEncoder (Reranker) Model ===")
    print(f"Base model: {args.model_name}")
    print(f"Epochs: {args.epochs}")
    print(f"Batch size: {args.batch_size}")
    print(f"Learning rate: {args.lr}")
    print(f"Output path: {output_path}")

    # 1. Load train dataset
    print("Loading training data (pairs with hard negatives)...")
    train_examples = []
    with open(train_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                query = data["query"]
                # Positive pair
                train_examples.append(InputExample(texts=[query, data["pos_doc_content"]], label=1.0))
                # Hard negative pairs
                for neg in data.get("hard_negatives", []):
                    train_examples.append(InputExample(texts=[query, neg["content"]], label=0.0))
    print(f"Loaded {len(train_examples)} training pairs (positive + hard negatives).")

    # 2. Load validation dataset
    print("Loading validation data...")
    val_samples = []
    with open(val_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                query = data["query"]
                positives = [data["pos_doc_content"]]
                negatives = [neg["content"] for neg in data.get("hard_negatives", [])]
                val_samples.append({
                    "query": query,
                    "positive": positives,
                    "negative": negatives
                })
    print(f"Loaded {len(val_samples)} validation samples.")

    # 3. Create Evaluator
    val_evaluator = CrossEncoderRerankingEvaluator(
        samples=val_samples,
        at_k=10,
        name="val_rerank",
        show_progress_bar=False
    )

    import torch
    torch.cuda.empty_cache()
    
    print(f"Loading CrossEncoder base model '{args.model_name}'...")
    # Jina Reranker v2 requires trust_remote_code=True
    model = CrossEncoder(
        args.model_name,
        num_labels=1,
        max_length=384,
        trust_remote_code=True
    )
    print(f"Model loaded on device: {model.model.device}")

    # Freeze embeddings and the first 8 layers of the encoder to save memory
    trainable_before = sum(p.numel() for p in model.model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.model.parameters())

    roberta = model.model.roberta
    for param in roberta.embeddings.parameters():
        param.requires_grad = False
    for i in range(8):
        for param in roberta.encoder.layers[i].parameters():
            param.requires_grad = False

    trainable_after = sum(p.numel() for p in model.model.parameters() if p.requires_grad)
    print(f"Layer Freezing: Trainable parameters reduced from {trainable_before:,} to {trainable_after:,} ({(trainable_after / total_params) * 100:.1f}% trainable)")

    # 5. Train
    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=args.batch_size)

    print("Starting fine-tuning...")
    model.fit(
        train_dataloader=train_dataloader,
        evaluator=val_evaluator,
        epochs=args.epochs,
        evaluation_steps=args.eval_steps,
        output_path=output_path,
        save_best_model=True,
        optimizer_class=Adafactor,
        optimizer_params={"lr": args.lr, "scale_parameter": False, "relative_step": False, "warmup_init": False},
        use_amp=False,
        warmup_steps=int(len(train_dataloader) * 0.1)
    )
    print(f"Training completed. Best model saved to: {output_path}")

if __name__ == "__main__":
    main()
