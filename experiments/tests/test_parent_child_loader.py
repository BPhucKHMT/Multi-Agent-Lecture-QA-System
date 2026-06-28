import json
from pathlib import Path

from experiments.src.data.chunk_loader import load_chunks


def test_load_chunks_reads_parent_child_child_files(tmp_path: Path):
    strategy_dir = tmp_path / "parent_child_180s_45s"
    child_file = strategy_dir / "cs101" / "child_chunks.json"
    child_file.parent.mkdir(parents=True)
    child_file.write_text(
        json.dumps(
            [
                {
                    "page_content": "Child content",
                    "metadata": {
                        "chunk_id": "video_a_child_10_40",
                        "parent_chunk_id": "video_a_parent_0_90",
                        "filename": "video_a",
                        "video_url": "https://youtu.be/a",
                        "start_timestamp": "0:00:10",
                        "end_timestamp": "0:00:40",
                    },
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    chunks = load_chunks(strategy_dir, strategy_id="parent_child_180s_45s")

    assert len(chunks) == 1
    assert chunks[0]["doc_id"] == "video_a_child_10_40"
    assert chunks[0]["metadata"]["parent_chunk_id"] == "video_a_parent_0_90"
