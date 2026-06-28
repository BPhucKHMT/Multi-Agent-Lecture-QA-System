import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "artifacts/chunks"
DEFAULT_STRATEGY_ID = "recursive"
DEFAULT_TARGET_ROOT = ROOT / "experiments/data/chunks"


def copy_strategy(source_dir: Path, target_dir: Path, strategy_id: str) -> int:
    files = sorted(source_dir.glob("**/semantic_chunks.json"))
    target_dir.mkdir(parents=True, exist_ok=True)
    for source_file in files:
        relative_path = source_file.relative_to(source_dir).with_name(f"{strategy_id}_chunks.json")
        target_file = target_dir / relative_path
        target_file.parent.mkdir(parents=True, exist_ok=True)
        if not target_file.exists():
            shutil.copy2(source_file, target_file)
    return len(files)


def main() -> None:
    parser = argparse.ArgumentParser(description="Mirror chunk strategy corpus into experiments/data/chunks.")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--strategy-id", default=DEFAULT_STRATEGY_ID)
    parser.add_argument("--target-dir", type=Path)
    args = parser.parse_args()

    target_dir = args.target_dir or DEFAULT_TARGET_ROOT / args.strategy_id
    copied_count = copy_strategy(args.source_dir, target_dir, args.strategy_id)
    print(f"Prepared {copied_count} {args.strategy_id} chunk files at {target_dir}")


if __name__ == "__main__":
    main()
