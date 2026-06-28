import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.src.data.chunk_loader import load_chunks


OUTPUT_DIR = ROOT / "experiments/data/processed"


def build_chunk_manifest(strategy_id: str, chunks_dir: Path) -> dict:
    chunks = load_chunks(chunks_dir, strategy_id=strategy_id)
    course_ids = {chunk["metadata"].get("course_id") for chunk in chunks}
    video_ids = {chunk["metadata"].get("filename") for chunk in chunks}
    missing_timestamp_count = sum(
        1
        for chunk in chunks
        if not chunk["metadata"].get("start_timestamp") or not chunk["metadata"].get("end_timestamp")
    )
    return {
        "strategy_id": strategy_id,
        "source_dir": str(chunks_dir),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chunk_count": len(chunks),
        "missing_timestamp_count": missing_timestamp_count,
        "course_count": len(course_ids),
        "video_count": len(video_ids),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build chunk manifest for one experiment strategy.")
    parser.add_argument("--strategy-id", default="recursive")
    parser.add_argument("--chunks-dir", type=Path, default=ROOT / "experiments/data/chunks/recursive")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = args.output or OUTPUT_DIR / f"chunk_manifest_{args.strategy_id}.json"
    manifest = build_chunk_manifest(args.strategy_id, args.chunks_dir)
    output_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated {output_path} with {manifest['chunk_count']} chunks.")


if __name__ == "__main__":
    main()
