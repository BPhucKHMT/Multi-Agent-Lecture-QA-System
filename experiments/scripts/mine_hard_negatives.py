from __future__ import annotations
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Mine hard negatives for training embedding/reranker models.")
    parser.add_argument("--batch-size", type=int, default=128, help="Batch size for similarity matrix calculation.")
    parser.add_argument("--limit-docs", type=int, default=None, help="Limit number of candidate docs to process for testing.")
    parser.add_argument("--model-name", type=str, default="BAAI/bge-m3", help="SentenceTransformer model name to use.")
    args = parser.parse_args()

    import torch
    torch.set_num_threads(4)

    # Load candidate documents (all recursive chunks)
    from experiments.src.data.chunk_loader import load_chunks
    chunks_dir = ROOT / "experiments/data/chunks/recursive"
    all_chunks = load_chunks(chunks_dir, strategy_id="recursive")
    print(f"Loaded {len(all_chunks)} candidate documents.")
    if args.limit_docs is not None:
        all_chunks = all_chunks[:args.limit_docs]
        print(f"Limiting to first {len(all_chunks)} candidate documents.")
        
    if not all_chunks:
        print("Error: No candidate documents found.")
        return

    # Load train and validation queries
    finetune_dir = ROOT / "experiments/data/finetune"
    train_file = finetune_dir / "train_queries.jsonl"
    val_file = finetune_dir / "val_queries.jsonl"
    
    if not train_file.exists() or not val_file.exists():
        print("Error: train_queries.jsonl or val_queries.jsonl does not exist. Run train_splits.py first.")
        return

    train_queries = []
    with open(train_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                train_queries.append(json.loads(line))

    val_queries = []
    with open(val_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                val_queries.append(json.loads(line))

    print(f"Loaded {len(train_queries)} train queries and {len(val_queries)} val queries.")

    # Initialize model
    from sentence_transformers import SentenceTransformer
    print(f"Loading {args.model_name} model...")
    model = SentenceTransformer(args.model_name)
    model.max_seq_length = 256

    print("Encoding all candidate documents...")
    doc_texts = [doc["text"] for doc in all_chunks]
    doc_embeddings = model.encode(doc_texts, batch_size=32, show_progress_bar=True, normalize_embeddings=True)
    doc_embeddings = np.array(doc_embeddings)
    doc_id_to_idx = {doc["doc_id"]: idx for idx, doc in enumerate(all_chunks)}

    def mine_negatives_for_split(queries: list[dict], output_path: Path, split_name: str):
        print(f"\nMining hard negatives for {split_name} queries...")
        query_texts = [q["query"] for q in queries]
        
        print("Encoding queries...")
        q_embeddings = model.encode(query_texts, batch_size=32, show_progress_bar=True, normalize_embeddings=True)
        q_embeddings = np.array(q_embeddings)

        print("Calculating similarity and selecting top-5 hard negatives...")
        with open(output_path, "w", encoding="utf-8") as out_f:
            for start_idx in range(0, len(queries), args.batch_size):
                end_idx = min(start_idx + args.batch_size, len(queries))
                batch_q = q_embeddings[start_idx:end_idx]
                
                # similarity shape: (batch_size, num_docs)
                sim_matrix = np.dot(batch_q, doc_embeddings.T)
                
                for i in range(len(batch_q)):
                    q_idx = start_idx + i
                    query_record = queries[q_idx]
                    pos_doc_id = query_record["pos_doc_id"]
                    
                    # Sort document indices by similarity in descending order
                    sorted_indices = np.argsort(sim_matrix[i])[::-1]
                    
                    hard_negatives = []
                    for doc_idx in sorted_indices:
                        doc = all_chunks[doc_idx]
                        if doc["doc_id"] == pos_doc_id:
                            continue
                        
                        score = float(sim_matrix[i][doc_idx])
                        hard_negatives.append({
                            "doc_id": doc["doc_id"],
                            "content": doc["text"],
                            "score": score
                        })
                        if len(hard_negatives) == 5:
                            break
                    
                    record = {
                        "query": query_record["query"],
                        "pos_doc_id": pos_doc_id,
                        "pos_doc_content": query_record["pos_doc_content"],
                        "course": query_record.get("course"),
                        "hard_negatives": hard_negatives,
                        "metadata": query_record.get("metadata")
                    }
                    out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    
        print(f"Finished mining for {split_name}. Output written to {output_path.name}.")

    mine_negatives_for_split(train_queries, finetune_dir / "train_hard_negatives.jsonl", "train")
    mine_negatives_for_split(val_queries, finetune_dir / "val_hard_negatives.jsonl", "val")
    print("\nHard negative mining completed successfully.")

if __name__ == "__main__":
    main()
