import json
from pathlib import Path

from experiments.src.data.qrels_loader import load_parent_qrels_from_child_qrels


def test_load_parent_qrels_from_child_qrels_collapses_children_to_parent(tmp_path: Path):
    qrels_path = tmp_path / "qrels.jsonl"
    qrels_path.write_text(
        "\n".join(
            [
                json.dumps({"query_id": "q1", "doc_id": "child_a", "relevance": 1}),
                json.dumps({"query_id": "q1", "doc_id": "child_b", "relevance": 2}),
                json.dumps({"query_id": "q1", "doc_id": "child_c", "relevance": 1}),
            ]
        ),
        encoding="utf-8",
    )
    child_chunks = [
        {"doc_id": "child_a", "metadata": {"parent_chunk_id": "parent_1"}},
        {"doc_id": "child_b", "metadata": {"parent_chunk_id": "parent_1"}},
        {"doc_id": "child_c", "metadata": {"parent_chunk_id": "parent_2"}},
    ]

    qrels = load_parent_qrels_from_child_qrels(qrels_path, child_chunks)

    assert qrels == {"q1": {"parent_1": 2, "parent_2": 1}}
