#!/usr/bin/env python
"""
Create qrels_semantic.jsonl from semantic chunks and ground truth.
Uses the same logic as load_dynamic_qrels but for semantic strategy.
"""

import sys
import json
from pathlib import Path

# Add experiments/src to path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments" / "src"))

from data.chunk_loader import load_chunks
from data.qrels_loader import load_dynamic_qrels

def create_semantic_qrels():
    # Paths
    chunks_dir = ROOT / "experiments" / "data" / "chunks" / "semantic"
    query_path = ROOT / "experiments" / "data" / "ground_truth" / "ground_truth_pilot.jsonl"
    qrels_output_path = ROOT / "experiments" / "data" / "processed" / "qrels_semantic.jsonl"

    if not chunks_dir.exists():
        print(f"[ERR] Semantic chunks dir not found: {chunks_dir}")
        return

    if not query_path.exists():
        print(f"[ERR] Ground truth not found: {query_path}")
        return

    print("[LOAD] Loading semantic chunks...")
    chunks = load_chunks(chunks_dir, strategy_id="semantic")
    print(f"  Loaded {len(chunks)} chunks")

    print("[LOAD] Loading ground truth queries...")
    qrels_dict = load_dynamic_qrels(query_path, chunks)
    # qrels_dict: Dict[query_id, DynamicQueryQrels]
    total_entries = sum(len(dq.db_relevant_docs) for dq in qrels_dict.values())
    print(f"  Generated {total_entries} qrels entries for {len(qrels_dict)} queries")

    # Write qrels in the same format as qrels_recursive.jsonl
    qrels_output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(qrels_output_path, "w", encoding="utf-8") as f:
        for query_id in sorted(qrels_dict.keys()):
            dq = qrels_dict[query_id]
            for doc_id, relevance in sorted(dq.db_relevant_docs.items()):
                f.write(json.dumps({
                    "query_id": query_id,
                    "doc_id": doc_id,
                    "relevance": relevance
                }) + "\n")

    print(f"[OK] Wrote qrels_semantic.jsonl to {qrels_output_path}")

if __name__ == "__main__":
    create_semantic_qrels()
