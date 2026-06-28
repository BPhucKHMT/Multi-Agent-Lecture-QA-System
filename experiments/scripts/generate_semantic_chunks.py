#!/usr/bin/env python
"""
Generate semantic chunks using LangChain's SemanticChunker with BGE-M3.
Output format: artifacts/chunks/<playlist>/semantic_chunks.json
"""

import json
import re
import argparse
import sys
import unicodedata
from pathlib import Path
from typing import List, Dict, Any
from difflib import SequenceMatcher

from langchain_experimental.text_splitter import SemanticChunker
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')

# Paths
ROOT = Path(__file__).resolve().parents[2]
PLAYLISTS_DATA_DIR = ROOT / "artifacts" / "data"
CHUNKS_OUTPUT_DIR = ROOT / "experiments" / "data" / "chunks" / "semantic"
OPENAI_CHUNKS_OUTPUT_DIR = ROOT / "experiments" / "data" / "chunks" / "semantic_openai_large"
FINETUNED_MODEL_PATH = ROOT / "experiments/runs/finetune/embedding/20260616-120132"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-large"
OPENAI_EMBEDDING_DIMENSIONS = 3072
OPENAI_EMBEDDING_CHUNK_SIZE = 256

# OCR constants (from combine_content.py)
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
    """Convert 'H:MM:SS' or 'MM:SS' to seconds."""
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
    """Remove noise patterns and normalize OCR text."""
    if not text:
        return ""

    # Remove noise patterns (watermark, footer)
    for pattern in NOISE_PATTERNS:
        text = re.sub(re.escape(pattern), "", text, flags=re.IGNORECASE)

    # Normalize whitespace
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    # Filter short lines (usually OCR noise)
    filtered_lines = [l for l in lines if len(l) > 2]

    return '\n'.join(filtered_lines)

def is_subset_or_similar(text1: str, text2: str) -> bool:
    """Check if text2 is a subset or very similar to text1."""
    if text1 in text2:
        return True

    ratio = SequenceMatcher(None, text1, text2).ratio()
    return ratio >= SIMILARITY_THRESHOLD

def dedup_ocr_frames(frames: List[Dict[str, Any]]) -> List[str]:
    """Deduplicate OCR frames sorted by timestamp."""
    if not frames:
        return []

    processed_frames = []
    for f in frames:
        t = f.get("text", "")
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

def load_ocr_data(playlist_name: str) -> Dict[str, List[Dict[str, Any]]]:
    """Load all OCR JSON files from ocr_output_final and group by video_id."""
    ocr_dir = ROOT / "artifacts" / "data_extraction" / "OCR" / "ocr_output_final" / playlist_name
    ocr_index = {}

    if not ocr_dir.exists():
        print(f"  [WARN] Không tìm thấy thư mục OCR: {ocr_dir}")
        return {}

    # Load metadata.json to map normalized title to video_id
    metadata_path = ROOT / "artifacts" / "data" / playlist_name / "metadata.json"
    title_to_id = {}
    if metadata_path.exists():
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
                for v in meta.get("videos", []):
                    title_norm = unicodedata.normalize('NFKD', v["title"]).encode('ascii', 'ignore').decode('utf-8').lower()
                    title_norm = re.sub(r'[^\w]', '', title_norm)
                    title_to_id[title_norm] = v["video_id"]
        except Exception as e:
            print(f"  [WARN] Lỗi đọc metadata để map OCR: {e}")

    for json_file in ocr_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                frames = json.load(f)

            # Map the JSON file stem to video_id via title_to_id
            stem_norm = unicodedata.normalize('NFKD', json_file.stem).encode('ascii', 'ignore').decode('utf-8').lower()
            stem_norm = re.sub(r'[^\w]', '', stem_norm)
            v_id = title_to_id.get(stem_norm, json_file.stem)

            # Normalize frames to (timestamp_s, text) format
            normalized_frames = []
            for fr in frames:
                txt = fr.get("text") or fr.get("ocr_text", "")
                ts = fr.get("timestamp_s")
                if ts is None:
                    ts = fr.get("timestamp_seconds", 0)

                normalized_frames.append({
                    "timestamp_s": float(ts),
                    "text": txt
                })

            ocr_index[v_id] = normalized_frames

        except Exception as e:
            print(f"  [WARN] Lỗi đọc file OCR {json_file}: {e}")

    # Sort each video's frames by timestamp
    for v_id in ocr_index:
        ocr_index[v_id].sort(key=lambda x: x.get("timestamp_s", 0))

    return ocr_index

def load_transcripts(playlist_dir: Path) -> List[Dict[str, Any]]:
    """Load all .txt transcripts from a playlist directory and enrich with metadata."""
    # Load metadata.json (in parent directory)
    metadata_path = playlist_dir.parent / "metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Missing metadata.json in {playlist_dir.parent}")

    with open(metadata_path, "r", encoding="utf-8") as f:
        playlist_metadata = json.load(f)

    playlist_name = playlist_metadata.get("playlist_id", playlist_dir.parent.name)
    playlist_title = playlist_metadata["title"]

    # Build video_id -> video_url and video_id -> video_title maps
    video_url_map = {}
    video_title_map = {}
    for video in playlist_metadata.get("videos", []):
        vid = video["video_id"]
        video_url_map[vid] = video["url"]
        video_title_map[vid] = video.get("title")

    transcripts = []
    txt_files = sorted(playlist_dir.glob("*.txt"))

    for txt_file in txt_files:
        video_id = txt_file.stem
        video_url = video_url_map.get(video_id)
        video_title = video_title_map.get(video_id, playlist_title)
        if video_url is None:
            print(f"  [WARN] No URL found for video {video_id}, skipping")
            continue

        with open(txt_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        full_text = ""
        position_map = []
        for line in lines:
            line = line.strip()
            if not line or "[âm nhạc]" in line.lower():
                continue
            match = re.match(r"(\d+:\d+:\d+)\s*-\s*(\d+:\d+:\d+),\s*(.+)", line)
            if match:
                start, end, text = match.groups()
                pos_start = len(full_text)
                text_stripped = text.strip()
                if text_stripped and text_stripped[-1] not in ".!?;":
                    full_text += text_stripped + ". "
                else:
                    full_text += text_stripped + " "
                pos_end = len(full_text)
                position_map.append({
                    "start": start,
                    "end": end,
                    "text": text_stripped,
                    "pos_start": pos_start,
                    "pos_end": pos_end
                })

        transcripts.append({
            "filename": video_id,
            "full_text": full_text.strip(),
            "position_map": position_map,
            "playlist": playlist_name,
            "title": video_title,
            "url": video_url
        })

    return transcripts

def create_embeddings(provider: str):
    """Khởi tạo embedding model cho SemanticChunker."""
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        load_dotenv()
        import os

        api_key = os.getenv("myAPIKey") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing OpenAI API key: set myAPIKey or OPENAI_API_KEY in .env")

        print(f"  [LOAD] Loading OpenAI embeddings: {OPENAI_EMBEDDING_MODEL}")
        return OpenAIEmbeddings(
            model=OPENAI_EMBEDDING_MODEL,
            api_key=api_key,
            dimensions=OPENAI_EMBEDDING_DIMENSIONS,
            chunk_size=OPENAI_EMBEDDING_CHUNK_SIZE,
        )

    if not FINETUNED_MODEL_PATH.exists():
        raise FileNotFoundError(f"Fine-tuned model not found at {FINETUNED_MODEL_PATH}")

    print("  [LOAD] Loading BGE-M3 embeddings...")
    return HuggingFaceEmbeddings(model_name=str(FINETUNED_MODEL_PATH))


def create_semantic_chunks(transcripts: List[Dict[str, Any]], output_dir: Path, ocr_index: Dict[str, List[Dict[str, Any]]], video_mapping: Dict[str, str], embedding_provider: str) -> List[Dict[str, Any]]:
    """Create semantic chunks from transcripts using SemanticChunker, enriched with OCR content."""
    output_dir.mkdir(parents=True, exist_ok=True)

    embeddings = create_embeddings(embedding_provider)

    # Initialize semantic splitter
    print("  [SPLIT] Initializing SemanticChunker...")
    text_splitter = SemanticChunker(
        embeddings=embeddings,
        buffer_size=1,
        add_start_index=True,
        breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=95
    )

    all_chunks = []
    for idx, transcript in enumerate(transcripts, 1):
        print(f"  Processing video {idx}/{len(transcripts)}: {transcript['filename']}")
        # Create Document from full_text
        doc = Document(
            page_content=transcript["full_text"],
            metadata={
                "playlist": transcript["playlist"],
                "video_url": transcript["url"],
                "filename": transcript["filename"],
                "title": transcript["title"]
            }
        )

        # Split
        docs = text_splitter.split_documents([doc])

        # Get OCR frames for this video with fallback matching
        video_id = transcript["filename"]
        video_title = transcript["title"]
        ocr_frames = None

        # Direct match by video_id
        if video_id in ocr_index:
            ocr_frames = ocr_index[video_id]
        else:
            # Fallback: match by normalized title
            v_title_norm = unicodedata.normalize('NFKD', video_title).encode('ascii', 'ignore').decode('utf-8').lower()
            v_title_norm = re.sub(r'[^\w]', '', v_title_norm)
            for ocr_key, frames in ocr_index.items():
                ocr_key_norm = unicodedata.normalize('NFKD', ocr_key).encode('ascii', 'ignore').decode('utf-8').lower()
                ocr_key_norm = re.sub(r'[^\w]', '', ocr_key_norm)
                if v_title_norm == ocr_key_norm or v_title_norm in ocr_key_norm or ocr_key_norm in v_title_norm:
                    ocr_frames = frames
                    print(f"    [INFO] Matched by title: '{video_title}' -> '{ocr_key}'")
                    break

        if ocr_frames is None:
            ocr_frames = []
            print(f"    [WARN] No OCR frames found for video {video_id}")

        for chunk_doc in docs:
            chunk_text = chunk_doc.page_content
            chunk_metadata = dict(chunk_doc.metadata)

            # Character indices
            start_idx = chunk_metadata.get("start_index", 0)
            end_idx = start_idx + len(chunk_text)

            # Find matching timestamps
            matched_ts = [
                ts for ts in transcript["position_map"]
                if not (ts["pos_end"] < start_idx or ts["pos_start"] > end_idx)
            ]

            if matched_ts:
                start_ts = matched_ts[0]["start"]
                end_ts = matched_ts[-1]["end"]
            else:
                start_ts = None
                end_ts = None

            # Find relevant OCR frames within chunk time range
            start_sec = timestamp_to_seconds(start_ts) if start_ts else 0
            end_sec = timestamp_to_seconds(end_ts) if end_ts else float('inf')

            relevant_frames = [
                f for f in ocr_frames
                if start_sec <= f.get("timestamp_s", 0) <= end_sec
            ]

            ocr_content = ""
            if relevant_frames:
                unique_texts = dedup_ocr_frames(relevant_frames)
                if unique_texts:
                    ocr_content = "\n---\n".join(unique_texts)

            final_metadata = {
                "playlist": transcript["playlist"],
                "video_url": transcript["url"],
                "filename": transcript["filename"],
                "title": transcript["title"],
                "chunk_id": len(all_chunks),
                "start_timestamp": start_ts,
                "end_timestamp": end_ts,
                "ocr_content": ocr_content
            }

            all_chunks.append({
                "page_content": chunk_text,
                "metadata": final_metadata
            })

    # Save
    output_path = output_dir / "semantic_chunks.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=4)

    print(f"  [OK] Total {len(all_chunks)} semantic chunks saved to {output_path}")
    return all_chunks

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--playlist", type=str, default=None, help="Specific playlist to process (optional)")
    parser.add_argument("--embedding-provider", choices=["bge", "openai"], default="bge")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    base_output_dir = args.output_dir or (OPENAI_CHUNKS_OUTPUT_DIR if args.embedding_provider == "openai" else CHUNKS_OUTPUT_DIR)

    # Get all playlist data directories
    all_playlist_dirs = [d for d in PLAYLISTS_DATA_DIR.iterdir() if d.is_dir()]

    if args.playlist:
        playlist_data_dirs = [d for d in all_playlist_dirs if d.name == args.playlist]
        if not playlist_data_dirs:
            print(f"[ERR] Playlist '{args.playlist}' not found in {PLAYLISTS_DATA_DIR}")
            return
    else:
        playlist_data_dirs = all_playlist_dirs

    for playlist_data_dir in playlist_data_dirs:
        transcripts_dir = playlist_data_dir / "processed_transcripts"
        if not transcripts_dir.exists():
            print(f"  [WARN] Skipping {playlist_data_dir.name}: no processed_transcripts")
            continue

        playlist_name = playlist_data_dir.name
        print(f"[DIR] Processing playlist: {playlist_name}")

        try:
            # Load transcripts
            transcripts = load_transcripts(transcripts_dir)
            print(f"  Loaded {len(transcripts)} videos")

            # Load OCR data
            ocr_index = load_ocr_data(playlist_name)
            if ocr_index:
                print(f"  Loaded OCR data for {len(ocr_index)} videos")
            else:
                print(f"  [WARN] No OCR data available")

            # Load metadata to get video_id -> title mapping for fallback matching
            metadata_path = ROOT / "artifacts" / "data" / playlist_name / "metadata.json"
            video_mapping = {}
            if metadata_path.exists():
                with open(metadata_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    for v in meta.get("videos", []):
                        video_mapping[v["video_id"]] = v["title"]
            else:
                print(f"  [WARN] No metadata.json found at {metadata_path}")

            # Create semantic chunks with OCR enrichment
            output_dir = base_output_dir / playlist_name
            create_semantic_chunks(transcripts, output_dir, ocr_index, video_mapping, args.embedding_provider)
        except Exception as e:
            print(f"  [ERR] Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
