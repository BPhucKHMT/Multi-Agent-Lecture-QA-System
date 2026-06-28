import json
from pathlib import Path

from experiments.scripts.generate_parent_child_chunks import build_parent_child_chunks, validate_child_parent_links


def _chunk(video_id: str, start: str, end: str, text: str) -> dict:
    return {
        "page_content": text,
        "metadata": {
            "filename": video_id,
            "video_url": "https://youtu.be/demo",
            "start_timestamp": start,
            "end_timestamp": end,
        },
    }


def test_build_parent_child_chunks_keeps_child_inside_single_parent():
    source_chunks = [
        _chunk("video_a", "0:00", "0:30", "intro"),
        _chunk("video_a", "0:30", "1:00", "routing"),
        _chunk("video_a", "1:00", "1:30", "agents"),
        _chunk("video_a", "1:30", "2:00", "retrieval"),
    ]

    parents, children, links = build_parent_child_chunks(
        source_chunks,
        parent_window_seconds=90,
        parent_overlap_seconds=30,
        child_window_seconds=30,
        child_overlap_seconds=0,
    )

    assert parents
    assert children
    assert len(links) == len(children)
    assert validate_child_parent_links(parents, children, links) == []
    assert all(child["metadata"]["parent_chunk_id"] for child in children)
    assert all(child["metadata"]["chunk_strategy"] == "parent_child_180s_45s" for child in children)


def test_build_parent_child_chunks_writes_stable_child_parent_ids():
    source_chunks = [
        _chunk("video_a", "0:00", "0:30", "intro"),
        _chunk("video_a", "0:30", "1:00", "routing"),
    ]

    parents, children, links = build_parent_child_chunks(
        source_chunks,
        parent_window_seconds=60,
        parent_overlap_seconds=0,
        child_window_seconds=30,
        child_overlap_seconds=0,
    )

    assert parents[0]["metadata"]["chunk_id"] == "video_a_parent_0_60"
    assert children[0]["metadata"]["chunk_id"] == "video_a_child_0_30"
    assert children[0]["metadata"]["parent_chunk_id"] == "video_a_parent_0_60"
    assert links[0] == {
        "child_chunk_id": "video_a_child_0_30",
        "parent_chunk_id": "video_a_parent_0_60",
        "video_id": "video_a",
        "child_start_seconds": 0,
        "child_end_seconds": 30,
        "parent_start_seconds": 0,
        "parent_end_seconds": 60,
    }
