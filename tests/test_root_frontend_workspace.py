from pathlib import Path


def test_root_frontend_workspace_exists_with_readme():
    root = Path(__file__).resolve().parents[1]
    frontend_dir = root / "frontend"
    readme_file = frontend_dir / "README.md"

    assert frontend_dir.is_dir(), "Expected root-level frontend/ directory."
    assert readme_file.is_file(), "Expected frontend/README.md placeholder guide."
