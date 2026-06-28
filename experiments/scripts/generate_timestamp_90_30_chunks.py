import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.src.time_utils import timestamp_to_seconds

DEFAULT_SOURCE = ROOT / "experiments/data/chunks/semantic"
DEFAULT_TARGET = ROOT / "experiments/data/chunks/timestamp_90_30"
STRATEGY_ID = "timestamp_90_30"
WINDOW_SECONDS = 90
OVERLAP_SECONDS = 30


def generate_strategy(source_dir: Path, target_dir: Path) -> int:
    source_files = sorted(source_dir.glob("**/semantic_chunks.json"))
    for source_file in source_files:
        chunks = json.loads(source_file.read_text(encoding="utf-8"))
        generated = build_timestamp_chunks(chunks)
        target_file = target_dir / source_file.relative_to(source_dir).with_name(f"{STRATEGY_ID}_chunks.json")
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(json.dumps(generated, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(source_files)


def build_timestamp_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_video: dict[str, list[dict[str, Any]]] = {}
    for chunk in chunks:
        metadata = chunk.get("metadata") or {}
        video_id = metadata.get("filename")
        if video_id:
            by_video.setdefault(video_id, []).append(chunk)

    generated: list[dict[str, Any]] = []
    for video_chunks in by_video.values():
        ordered = sorted(video_chunks, key=chunk_start)
        generated.extend(build_video_windows(ordered))
    return generated


def build_video_windows(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not chunks:
        return []

    video_start = min(chunk_start(chunk) for chunk in chunks)
    video_end = max(chunk_end(chunk) for chunk in chunks)
    stride = WINDOW_SECONDS - OVERLAP_SECONDS
    windows = []
    start = video_start
    while start < video_end:
        end = min(start + WINDOW_SECONDS, video_end)
        window_chunks = [chunk for chunk in chunks if overlaps(chunk, start, end)]
        if window_chunks:
            windows.append(to_window_chunk(window_chunks, start, end))
        start += stride
    return windows


def to_window_chunk(chunks: list[dict[str, Any]], start: int, end: int) -> dict[str, Any]:
    base_metadata = dict(chunks[0].get("metadata") or {})
    base_metadata["start_timestamp"] = seconds_to_timestamp(start)
    base_metadata["end_timestamp"] = seconds_to_timestamp(end)
    base_metadata["chunk_strategy"] = STRATEGY_ID
    base_metadata["window_seconds"] = WINDOW_SECONDS
    base_metadata["overlap_seconds"] = OVERLAP_SECONDS

    return {
        "page_content": "\n".join(chunk.get("page_content", "").strip() for chunk in chunks if chunk.get("page_content")),
        "metadata": base_metadata,
    }


def overlaps(chunk: dict[str, Any], start: int, end: int) -> bool:
    return chunk_start(chunk) < end and chunk_end(chunk) > start


def chunk_start(chunk: dict[str, Any]) -> int:
    return timestamp_to_seconds((chunk.get("metadata") or {}).get("start_timestamp"))


def chunk_end(chunk: dict[str, Any]) -> int:
    return timestamp_to_seconds((chunk.get("metadata") or {}).get("end_timestamp"))


def seconds_to_timestamp(value: int) -> str:
    hours, remainder = divmod(value, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate timestamp_90_30 chunk assets.")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target-dir", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()

    file_count = generate_strategy(args.source_dir, args.target_dir)
    print(f"Generated {file_count} {STRATEGY_ID} chunk files at {args.target_dir}")


if __name__ == "__main__":
    main()
