import json
import csv
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GT_PATH = ROOT / "experiments/data/ground_truth/ground_truth_pilot.jsonl"
GT_BACKUP = ROOT / "experiments/data/ground_truth/ground_truth_pilot.jsonl.bak"
GT_CSV_PATH = ROOT / "experiments/data/ground_truth/ground_truth_pilot_review.csv"

# 1. Back up original file
if GT_PATH.exists() and not GT_BACKUP.exists():
    shutil.copy2(GT_PATH, GT_BACKUP)
    print(f"Backed up groundtruth to: {GT_BACKUP}")

# 2. Read all lines
records = []
with open(GT_PATH, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            records.append(json.loads(line))

print(f"Loaded {len(records)} records.")

# 3. Normalize category spelling
cat_mapping = {
    "So sánh": "comparison",
    "so sánh": "comparison",
    "Comparison": "comparison",
    "comparison": "comparison",
    "Mechanism": "mechanism",
    "mechanism": "mechanism",
    "Định nghĩa": "definition",
    "Definition": "definition",
    "definition": "definition",
    "ứng dụng": "application",
    "application": "application",
}

def normalize_timestamp(ts: str) -> str:
    if not ts:
        return ts
    parts = ts.strip().split(":")
    try:
        parts_int = [int(p) for p in parts]
    except ValueError:
        return ts
    if len(parts_int) == 3:
        h, m, s = parts_int
        return f"{h}:{m:02d}:{s:02d}"
    elif len(parts_int) == 2:
        m, s = parts_int
        return f"{m}:{s:02d}"
    return ts

for r in records:
    cat = r.get("category")
    if cat in cat_mapping:
        r["category"] = cat_mapping[cat]
    
    # Normalize evidence timestamps
    evidences = r.get("evidence", [])
    for ev in evidences:
        if "start_timestamp" in ev:
            ev["start_timestamp"] = normalize_timestamp(ev["start_timestamp"])
        if "end_timestamp" in ev:
            ev["end_timestamp"] = normalize_timestamp(ev["end_timestamp"])

# 4. Group records
# Group 1: CS114 (answerable)
# Group 2: CS116 (answerable)
# Group 3: CS315 (answerable)
# Group 4: CS431 (answerable)
# Group 5: no_answer (any course)

cs114_ans = [r for r in records if r.get("course_id") == "CS114" and r.get("category") != "no_answer"]
cs116_ans = [r for r in records if r.get("course_id") == "CS116" and r.get("category") != "no_answer"]
cs315_ans = [r for r in records if r.get("course_id") == "CS315" and r.get("category") != "no_answer"]
cs431_ans = [r for r in records if r.get("course_id") == "CS431" and r.get("category") != "no_answer"]
no_ans = [r for r in records if r.get("category") == "no_answer"]

grouped_records = cs114_ans + cs116_ans + cs315_ans + cs431_ans + no_ans

print(f"CS114 answerable: {len(cs114_ans)}")
print(f"CS116 answerable: {len(cs116_ans)}")
print(f"CS315 answerable: {len(cs315_ans)}")
print(f"CS431 answerable: {len(cs431_ans)}")
print(f"No answer: {len(no_ans)}")
print(f"Total grouped: {len(grouped_records)}")

# 5. Reassign IDs sequentially from q001 to q350
for idx, r in enumerate(grouped_records, start=1):
    r["id"] = f"q{idx:03d}"

# 6. Save back to groundtruth (JSONL)
with open(GT_PATH, "w", encoding="utf-8") as f:
    for r in grouped_records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"Saved normalized and grouped groundtruth to: {GT_PATH}")

# 7. Save back to groundtruth (CSV)
max_evidences = max(len(r.get("evidence", [])) for r in grouped_records) if grouped_records else 0
print(f"Max evidence count: {max_evidences}")

csv_rows = []
for r in grouped_records:
    evidences = r.get("evidence", [])
    row = {
        "id": r.get("id"),
        "course_id": r.get("course_id", ""),
        "question": r.get("question", ""),
        "answer": r.get("answer", ""),
        "topic": r.get("topic", ""),
        "category": r.get("category", ""),
        "level": r.get("level", ""),
        "status": r.get("status", ""),
        "evidence_count": len(evidences),
        "note": r.get("note", "")
    }
    for i in range(1, max_evidences + 1):
        if i <= len(evidences):
            ev = evidences[i-1]
            row[f"evidence_{i}_video_id"] = ev.get("video_id", "")
            row[f"evidence_{i}_video_url"] = ev.get("video_url", "")
            row[f"evidence_{i}_start_timestamp"] = ev.get("start_timestamp", "")
            row[f"evidence_{i}_end_timestamp"] = ev.get("end_timestamp", "")
            row[f"evidence_{i}_score"] = ev.get("score", "")
        else:
            row[f"evidence_{i}_video_id"] = ""
            row[f"evidence_{i}_video_url"] = ""
            row[f"evidence_{i}_start_timestamp"] = ""
            row[f"evidence_{i}_end_timestamp"] = ""
            row[f"evidence_{i}_score"] = ""
    csv_rows.append(row)

fieldnames = [
    "id", "course_id", "question", "answer", "topic", "category", "level", "status",
    "evidence_count"
]
for i in range(1, max_evidences + 1):
    fieldnames.extend([
        f"evidence_{i}_video_id",
        f"evidence_{i}_video_url",
        f"evidence_{i}_start_timestamp",
        f"evidence_{i}_end_timestamp",
        f"evidence_{i}_score"
    ])
fieldnames.append("note")

with open(GT_CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for row in csv_rows:
        writer.writerow(row)

print(f"Saved normalized and grouped groundtruth to: {GT_CSV_PATH}")
