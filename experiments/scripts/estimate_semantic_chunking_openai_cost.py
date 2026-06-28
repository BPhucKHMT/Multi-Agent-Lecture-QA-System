import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.scripts.generate_semantic_chunks import PLAYLISTS_DATA_DIR, load_transcripts
from experiments.scripts.estimate_openai_embedding_cost import estimate_tokens

PRICE_PER_1M_TOKENS = 0.13
MODEL_NAME = "text-embedding-3-large"


def iter_transcript_dirs(playlist: str | None):
    for playlist_dir in sorted(PLAYLISTS_DATA_DIR.iterdir()):
        if not playlist_dir.is_dir():
            continue
        if playlist and playlist_dir.name != playlist:
            continue
        transcripts_dir = playlist_dir / "processed_transcripts"
        if transcripts_dir.exists():
            yield transcripts_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Estimate SemanticChunker OpenAI input cost without API calls.")
    parser.add_argument("--playlist", default=None)
    args = parser.parse_args()

    texts = []
    video_count = 0
    for transcripts_dir in iter_transcript_dirs(args.playlist):
        transcripts = load_transcripts(transcripts_dir)
        video_count += len(transcripts)
        texts.extend(t["full_text"] for t in transcripts)

    total_tokens = estimate_tokens(texts, MODEL_NAME)
    print(json.dumps({
        "model": MODEL_NAME,
        "videos": video_count,
        "total_tokens": total_tokens,
        "estimated_usd": round(total_tokens / 1_000_000 * PRICE_PER_1M_TOKENS, 6),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
