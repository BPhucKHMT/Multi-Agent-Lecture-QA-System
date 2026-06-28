from __future__ import annotations
import json
import random
import sys
import argparse
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

def main():
    parser = argparse.ArgumentParser(description="Split queries into train/val sets.")
    parser.add_argument("--input-file", type=str, default=None, help="Path to input queries file.")
    args = parser.parse_args()

    # Auto-detect input file if not specified
    if args.input_file:
        input_file = Path(args.input_file)
    else:
        augmented_file = ROOT / "experiments/data/finetune/synthetic_queries_augmented.jsonl"
        if augmented_file.exists():
            input_file = augmented_file
        else:
            input_file = ROOT / "experiments/data/finetune/synthetic_queries.jsonl"

    if not input_file.exists():
        print(f"Error: {input_file} does not exist. Run query generation/augmentation first.")
        return

    records = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print(f"Loaded {len(records)} queries from {input_file.name}.")
    if not records:
        return

    # Group by course and pos_doc_id to prevent data leakage
    # Structure: course -> pos_doc_id -> list of records
    by_course_and_doc = defaultdict(lambda: defaultdict(list))
    for r in records:
        course = r.get("course", "UNKNOWN")
        doc_id = r.get("pos_doc_id", "UNKNOWN_DOC")
        by_course_and_doc[course][doc_id].append(r)

    train_records = []
    val_records = []

    print("\nSplitting by course and grouping by pos_doc_id (stratified 95% train / 5% val):")
    random.seed(42)
    for course, docs_dict in sorted(by_course_and_doc.items()):
        doc_ids = list(docs_dict.keys())
        random.shuffle(doc_ids)
        
        split_idx = int(len(doc_ids) * 0.95)
        if split_idx == len(doc_ids) and len(doc_ids) > 1:
            split_idx = len(doc_ids) - 1
        elif len(doc_ids) == 1:
            split_idx = 1 # Put the single doc in train
            
        train_doc_ids = doc_ids[:split_idx]
        val_doc_ids = doc_ids[split_idx:]
        
        train_c = []
        for doc_id in train_doc_ids:
            train_c.extend(docs_dict[doc_id])
            
        val_c = []
        for doc_id in val_doc_ids:
            val_c.extend(docs_dict[doc_id])
            
        train_records.extend(train_c)
        val_records.extend(val_c)
        print(f"  Course {course}: unique_docs={len(doc_ids)}, train_queries={len(train_c)}, val_queries={len(val_c)}")

    # Write splits
    output_dir = ROOT / "experiments/data/finetune"
    train_file = output_dir / "train_queries.jsonl"
    val_file = output_dir / "val_queries.jsonl"

    with open(train_file, "w", encoding="utf-8") as f:
        for r in train_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(val_file, "w", encoding="utf-8") as f:
        for r in val_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\nWritten {len(train_records)} training queries to {train_file.name}.")
    print(f"Written {len(val_records)} validation queries to {val_file.name}.")

if __name__ == "__main__":
    main()
