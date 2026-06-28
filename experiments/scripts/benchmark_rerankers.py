import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.src.reranker.benchmark import run_reranker_benchmark


def load_config(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml

        config = yaml.safe_load(text)
    except ModuleNotFoundError:
        config = json.loads(text)
    return resolve_paths(config)


def resolve_paths(config: dict[str, Any]) -> dict[str, Any]:
    resolved = dict(config)
    for key in ("chunks_dir", "query_path", "qrels_path", "run_root", "registry_path"):
        resolved[key] = str((ROOT / resolved[key]).resolve())
    return resolved


def list_models(config: dict[str, Any]) -> None:
    for model in config.get("models", []):
        status = "enabled" if model.get("enabled", True) else f"disabled:{model.get('optional_reason', '')}"
        lanes = ",".join(model.get("lanes", []))
        print(f"- {model['name']} | {model.get('type')} | {status} | lanes={lanes}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark reranker models with fixed candidate sets.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--only", nargs="*")
    parser.add_argument("--list-models", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.list_models:
        list_models(config)
        return
    run_dir = run_reranker_benchmark(config, limit=args.limit, only=set(args.only or []) or None)
    print(f"Completed reranker benchmark: {run_dir}")
    print(f"Summary: {run_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
