import os
import json
import re
from pathlib import Path
from difflib import SequenceMatcher
from typing import List, Dict, Any

# Constants
SIMILARITY_THRESHOLD = 0.85
MIN_OCR_LENGTH = 2
NOISE_PATTERNS = [
    "Trường Đại học Công nghệ Thông tin",
    "ĐHQG-HCM",
    "đhqg-hcm",
    "HCMCity University of Technology",
    "VNU-HCM",
]

def timestamp_to_seconds(ts: str) -> float:
    if not ts:
        return 0.0
    try:
        parts = ts.split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(ts)
    except (ValueError, TypeError):
        return 0.0

def clean_ocr_text(text: str) -> str:
    if not text:
        return ""
    for pattern in NOISE_PATTERNS:
        text = re.sub(re.escape(pattern), "", text, flags=re.IGNORECASE)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    filtered_lines = [l for l in lines if len(l) > 2]
    return '\n'.join(filtered_lines)

def is_subset_or_similar(text1: str, text2: str) -> bool:
    if text1 in text2:
        return True
    ratio = SequenceMatcher(None, text1, text2).ratio()
    return ratio >= SIMILARITY_THRESHOLD

def dedup_ocr_frames(frames: List[Dict[str, Any]]) -> List[str]:
    if not frames:
        return []
    processed_frames = []
    for f in frames:
        t = f.get("ocr_text") or f.get("text", "")
        t = clean_ocr_text(t)
        if len(t) >= MIN_OCR_LENGTH:
            processed_frames.append(t)
    if not processed_frames:
        return []
    unique_texts = []
    last_kept = ""
    for current in processed_frames:
        if not last_kept:
            unique_texts.append(current)
            last_kept = current
            continue
        if is_subset_or_similar(last_kept, current):
            unique_texts[-1] = current
            last_kept = current
        elif is_subset_or_similar(current, last_kept):
            continue
        else:
            unique_texts.append(current)
            last_kept = current
    return unique_texts

def build_ocr_index(ocr_dir: Path) -> Dict[str, List[Dict[str, Any]]]:
    ocr_index = {}
    if not ocr_dir.exists():
        return {}
    for json_file in ocr_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                frames = json.load(f)
            v_id = None
            if frames and isinstance(frames, list):
                v_id = frames[0].get("video_id")
            if not v_id:
                v_id = json_file.stem
            normalized_frames = []
            for fr in frames:
                txt = fr.get("ocr_text") or fr.get("text", "")
                ts = fr.get("timestamp_seconds") or fr.get("timestamp_s", 0)
                normalized_frames.append({
                    "timestamp_s": float(ts),
                    "text": txt
                })
            ocr_index[v_id] = normalized_frames
        except Exception as e:
            print(f"ERROR: Lỗi đọc file OCR {json_file}: {e}")
    for v_id in ocr_index:
        ocr_index[v_id].sort(key=lambda x: x.get("timestamp_s", 0))
    return ocr_index

def combine_all():
    root = Path("artifacts")
    chunks_root = root / "chunks"
    ocr_root = root / "data_extraction" / "OCR" / "ocr_output_final"
    
    if not chunks_root.exists():
        print(f"Chunks directory not found: {chunks_root}")
        return

    playlists = [d.name for d in chunks_root.iterdir() if d.is_dir()]
    
    for playlist_folder in playlists:
        chunks_file = chunks_root / playlist_folder / "semantic_chunks.json"
        ocr_dir = ocr_root / playlist_folder
        
        if not chunks_file.exists():
            continue
        if not ocr_dir.exists():
            print(f"OCR directory not found for: {playlist_folder} (skipping)")
            continue

        print(f"Processing playlist: {playlist_folder.encode('ascii', 'ignore').decode('ascii')}...")
        try:
            with open(chunks_file, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
            
            ocr_index = build_ocr_index(ocr_dir)
            enriched_count = 0
            
            for chunk in chunks:
                metadata = chunk.get("metadata", {})
                v_id = metadata.get("filename")
                if v_id and v_id in ocr_index:
                    ocr_frames = ocr_index[v_id]
                    start_sec = timestamp_to_seconds(metadata.get("start_timestamp"))
                    end_sec = timestamp_to_seconds(metadata.get("end_timestamp"))
                    relevant_frames = [
                        f for f in ocr_frames
                        if start_sec <= f.get("timestamp_s", 0) <= end_sec
                    ]
                    if relevant_frames:
                        unique_texts = dedup_ocr_frames(relevant_frames)
                        if unique_texts:
                            chunk["metadata"]["ocr_content"] = "\n---\n".join(unique_texts)
                            enriched_count += 1
                            
            if enriched_count > 0:
                output_file = chunks_file.parent / "semantic_chunks_with_ocr.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(chunks, f, ensure_ascii=False, indent=4)
                print(f"Success: Enriched {enriched_count}/{len(chunks)} chunks.")
            else:
                print(f"No chunks were enriched for {playlist_folder}.")
        except Exception as e:
            print(f"Error processing {playlist_folder}: {e}")

if __name__ == "__main__":
    combine_all()
