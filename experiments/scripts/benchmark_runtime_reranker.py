import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.scripts.benchmark_rerankers import load_config
from experiments.src.reranker.benchmark import run_reranker_benchmark


def build_config(
    config_path: Path,
    candidate_source: Path,
    pool_sizes: list[int] | None = None,
) -> dict[str, Any]:
    config = load_config(config_path)
    source = candidate_source.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    config["candidate_source_path"] = str(source)
    if pool_sizes:
        configured = {
            int(pool)
            for lane in config["lanes"].values()
            for pool in lane["candidate_pool_sizes"]
        }
        unknown = set(pool_sizes) - configured
        if unknown:
            raise ValueError(
                f"Candidate pools không có trong config: {sorted(unknown)}"
            )
        for lane in config["lanes"].values():
            lane["candidate_pool_sizes"] = [
                pool
                for pool in pool_sizes
                if pool in lane["candidate_pool_sizes"]
            ]
    return config


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run runtime-backend reranker ablation on fixed candidates."
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--candidate-source", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--pools", nargs="+", type=int)
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()

    config = build_config(
        args.config,
        args.candidate_source,
        pool_sizes=args.pools,
    )
    run_dir = run_reranker_benchmark(
        config,
        limit=args.limit,
        only=set(args.only or []) or None,
        offset=args.offset,
    )
    print(run_dir)


if __name__ == "__main__":
    main()
