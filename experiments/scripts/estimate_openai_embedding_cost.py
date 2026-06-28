import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.scripts.benchmark_embeddings import load_config, resolve_paths
from experiments.src.data.chunk_loader import load_chunks

PRICE_PER_1M_TOKENS = {
    "text-embedding-3-small": 0.02,
    "text-embedding-3-large": 0.13,
}


def estimate_tokens(texts: list[str], model_name: str) -> int:
    try:
        import tiktoken
        encoding = tiktoken.encoding_for_model(model_name)
        return sum(len(encoding.encode(text)) for text in texts)
    except Exception:
        return sum(max(1, len(text) // 4) for text in texts)


def estimate_config_cost(config: dict[str, Any]) -> dict[str, Any]:
    chunks = load_chunks(config["chunks_dir"], strategy_id=config["strategy_id"])
    query_rows = [json.loads(line) for line in Path(config["query_path"]).read_text(encoding="utf-8").splitlines() if line.strip()]
    model_name = config["model"]["name"]
    chunk_tokens = estimate_tokens([chunk["text"] for chunk in chunks], model_name)
    query_tokens = estimate_tokens([row["question"] for row in query_rows], model_name)
    total_tokens = chunk_tokens + query_tokens
    price = PRICE_PER_1M_TOKENS.get(model_name, 0.0)
    return {
        "model": model_name,
        "strategy_id": config["strategy_id"],
        "chunks": len(chunks),
        "queries": len(query_rows),
        "chunk_tokens": chunk_tokens,
        "query_tokens": query_tokens,
        "total_tokens": total_tokens,
        "estimated_usd": round(total_tokens / 1_000_000 * price, 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Estimate OpenAI embedding cost without calling API.")
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()

    config = resolve_paths(load_config(args.config))
    print(json.dumps(estimate_config_cost(config), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
