import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.scripts.embedding_factory import create_embedder
from experiments.src.indexing.chroma_index import build_chroma_index


def load_config(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml

        config = yaml.safe_load(text)
    except ModuleNotFoundError:
        config = json.loads(text)
    config["__config_path"] = str(path)
    return config


def resolve_paths(config: dict[str, Any]) -> dict[str, Any]:
    resolved = dict(config)
    for key in ("chunks_dir", "index_dir"):
        resolved[key] = str((ROOT / resolved[key]).resolve())
    return resolved


def main() -> None:
    parser = argparse.ArgumentParser(description="Build reusable embedding index for experiments.")
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()

    config = resolve_paths(load_config(args.config))
    embedder = create_embedder(config["model"])
    manifest = build_chroma_index(config, embedder)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
