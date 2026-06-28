import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.scripts.embedding_factory import create_embedder
from experiments.src.benchmark.hybrid_retrieval import run_hybrid_benchmark


def load_config(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml

        config = yaml.safe_load(text)
    except ModuleNotFoundError:
        config = json.loads(text)
    config["__config_path"] = str(path)
    return config


def resolve_paths(config: Dict[str, Any]) -> Dict[str, Any]:
    resolved = dict(config)
    for key in ("chunks_dir", "index_dir", "query_path", "qrels_path", "run_root", "registry_path"):
        resolved[key] = str((ROOT / resolved[key]).resolve())
    return resolved


def iter_model_configs(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "models" in config:
        return list(config["models"])
    return [config["model"]]


def build_model_run_config(config: Dict[str, Any], model_config: Dict[str, Any]) -> Dict[str, Any]:
    model_run_config = copy.deepcopy(config)
    model_run_config["model"] = model_config
    model_run_config.pop("models", None)
    return model_run_config


def run_model(config: Dict[str, Any], model_config: Dict[str, Any], limit: Optional[int]) -> Dict[str, Any]:
    embedder = create_embedder(model_config)
    run_dir = run_hybrid_benchmark(
        config=build_model_run_config(config, model_config),
        embedder=embedder,
        limit=limit,
    )
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    return {"model": model_config["name"], "run_dir": str(run_dir), "metrics": metrics}


def print_summary(results: List[Dict[str, Any]]) -> None:
    print("\nCompleted hybrid runs:")
    for result in results:
        metrics = result["metrics"]
        recall_new_40_str = f" R_new@40={metrics.get('recall_new@40')}" if 'recall_new@40' in metrics else ""
        print(
            f"- {result['model']} | "
            f"Hit@5={metrics.get('hit@5')} R@40={metrics.get('recall@40')}{recall_new_40_str} "
            f"MRR@10={metrics.get('mrr@10')} NDCG@10={metrics.get('ndcg@10')} | {result['run_dir']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark hybrid 0.5/0.5 retrieval for experiment chunk strategy.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    config = resolve_paths(load_config(args.config))
    model_configs = iter_model_configs(config)
    results = []
    for index, model_config in enumerate(model_configs, start=1):
        print(f"[{index}/{len(model_configs)}] Running hybrid {model_config['name']}...")
        results.append(run_model(config, model_config, args.limit))
    print_summary(results)


if __name__ == "__main__":
    main()
