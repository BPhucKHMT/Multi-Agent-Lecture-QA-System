from __future__ import annotations
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

def compute_cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    a = np.array(vec1)
    b = np.array(vec2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

def main():
    queries_file = ROOT / "experiments/data/finetune/synthetic_queries.jsonl"
    if not queries_file.exists():
        print(f"Error: {queries_file} does not exist. Run query generation first.")
        return

    records = []
    with open(queries_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print(f"=== Synthetic Queries Audit ===")
    print(f"Total queries generated: {len(records)}")
    if not records:
        return

    # Check duplicates
    query_texts = [r["query"] for r in records]
    unique_queries = set(query_texts)
    duplicate_count = len(query_texts) - len(unique_queries)
    print(f"Unique queries: {len(unique_queries)}")
    print(f"Duplicate queries: {duplicate_count}")

    # Check query lengths
    lengths = [len(q.split()) for q in query_texts]
    print(f"Query word length: min={min(lengths)}, max={max(lengths)}, avg={np.mean(lengths):.2f}")

    # Compute similarity with source chunks using SentenceTransformer
    try:
        from sentence_transformers import SentenceTransformer
        print("Loading BAAI/bge-m3 to calculate query-chunk similarities...")
        model = SentenceTransformer("BAAI/bge-m3")
        model.max_seq_length = 256
        
        # Unique source chunks
        doc_ids = list(set(r["pos_doc_id"] for r in records))
        doc_id_to_content = {r["pos_doc_id"]: r["pos_doc_content"] for r in records}
        
        print("Encoding source documents...")
        doc_embeddings = model.encode([doc_id_to_content[d] for d in doc_ids], show_progress_bar=False)
        doc_emb_map = {d: emb for d, emb in zip(doc_ids, doc_embeddings)}
        
        print("Encoding queries...")
        query_embeddings = model.encode(query_texts, show_progress_bar=False)
        
        similarities = []
        for r, q_emb in zip(records, query_embeddings):
            d_emb = doc_emb_map[r["pos_doc_id"]]
            sim = compute_cosine_similarity(q_emb, d_emb)
            similarities.append(sim)
            
        print(f"Query-Document Cosine Similarity (bge-m3):")
        print(f"  min: {min(similarities):.4f}")
        print(f"  max: {max(similarities):.4f}")
        print(f"  avg: {np.mean(similarities):.4f}")
        
    except Exception as e:
        print(f"Could not compute semantic similarity: {e}")

if __name__ == "__main__":
    main()
