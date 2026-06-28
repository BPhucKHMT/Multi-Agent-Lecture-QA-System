import json
from pathlib import Path

from experiments.src.data.chunk_loader import load_chunks
from experiments.src.data.qrels_loader import load_qrels


def write_chunk_file(path: Path, video_id: str = "video_a") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            [
                {
                    "page_content": "Nội dung chunk",
                    "metadata": {
                        "filename": video_id,
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


def test_load_chunks_reads_recursive_chunk_files(tmp_path: Path):
    strategy_dir = tmp_path / "recursive"
    chunk_file = strategy_dir / "cs101" / "recursive_chunks.json"
    write_chunk_file(chunk_file)

    chunks = load_chunks(strategy_dir)

    assert chunks == [
        {
            "doc_id": "video_a_10_40",
            "text": "Nội dung chunk",
            "metadata": {
                "filename": "video_a",
                "video_url": "https://youtu.be/a",
                "start_timestamp": "0:00:10",
                "end_timestamp": "0:00:40",
                "start_seconds": 10,
                "end_seconds": 40,
                "course_id": "CS101",
                "source_file": str(chunk_file),
            },
        }
    ]


def test_load_chunks_ignores_numeric_source_chunk_id(tmp_path: Path):
    strategy_dir = tmp_path / "recursive"
    chunk_file = strategy_dir / "cs101" / "recursive_chunks.json"
    write_chunk_file(chunk_file)
    chunks_data = json.loads(chunk_file.read_text(encoding="utf-8"))
    chunks_data[0]["metadata"]["chunk_id"] = 7
    chunk_file.write_text(json.dumps(chunks_data, ensure_ascii=False), encoding="utf-8")

    chunks = load_chunks(strategy_dir)

    assert chunks[0]["doc_id"] == "video_a_10_40"


def test_load_chunks_reads_strategy_specific_chunk_files(tmp_path: Path):
    strategy_dir = tmp_path / "timestamp_90_30"
    recursive_file = strategy_dir / "cs101" / "recursive_chunks.json"
    timestamp_file = strategy_dir / "cs101" / "timestamp_90_30_chunks.json"
    write_chunk_file(recursive_file, video_id="wrong_video")
    write_chunk_file(timestamp_file, video_id="right_video")

    chunks = load_chunks(strategy_dir, strategy_id="timestamp_90_30")

    assert len(chunks) == 1
    assert chunks[0]["doc_id"] == "right_video_10_40"
    assert chunks[0]["metadata"]["source_file"] == str(timestamp_file)


def test_load_qrels_keeps_highest_duplicate_relevance(tmp_path: Path):
    qrels_path = tmp_path / "qrels.jsonl"
    qrels_path.write_text(
        "\n".join(
            [
                json.dumps({"query_id": "q1", "doc_id": "d1", "relevance": 1}),
                json.dumps({"query_id": "q1", "doc_id": "d1", "relevance": 3}),
                json.dumps({"query_id": "q1", "doc_id": "d2", "relevance": 2}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    assert load_qrels(qrels_path) == {"q1": {"d1": 3, "d2": 2}}
