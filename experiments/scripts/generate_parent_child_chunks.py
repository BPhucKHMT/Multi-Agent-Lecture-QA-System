import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.src.time_utils import timestamp_to_seconds

DEFAULT_SOURCE = ROOT / "experiments/data/chunks/semantic"
DEFAULT_TARGET = ROOT / "experiments/data/chunks/parent_child_180s_45s"
STRATEGY_ID = "parent_child_180s_45s"
PARENT_WINDOW_SECONDS = 180
PARENT_OVERLAP_SECONDS = 60
CHILD_WINDOW_SECONDS = 45
CHILD_OVERLAP_SECONDS = 15


def generate_strategy(source_dir: Path, target_dir: Path) -> dict[str, int]:
    source_files = sorted(source_dir.glob("**/semantic_chunks.json"))
    parent_total = 0
    child_total = 0
    link_total = 0

    for source_file in source_files:
        chunks = json.loads(source_file.read_text(encoding="utf-8"))
        parents, children, links = build_parent_child_chunks(chunks)
        errors = validate_child_parent_links(parents, children, links)
        if errors:
            raise ValueError(f"Invalid parent-child mapping in {source_file}: {errors[:3]}")

        target_course_dir = target_dir / source_file.relative_to(source_dir).parent
        target_course_dir.mkdir(parents=True, exist_ok=True)
        write_json(target_course_dir / "parent_chunks.json", parents)
        write_json(target_course_dir / "child_chunks.json", children)
        write_jsonl(target_course_dir / "child_parent_map.jsonl", links)

        parent_total += len(parents)
        child_total += len(children)
        link_total += len(links)

    return {"file_count": len(source_files), "parent_count": parent_total, "child_count": child_total, "link_count": link_total}


def build_parent_child_chunks(
    chunks: list[dict[str, Any]],
    parent_window_seconds: int = PARENT_WINDOW_SECONDS,
    parent_overlap_seconds: int = PARENT_OVERLAP_SECONDS,
    child_window_seconds: int = CHILD_WINDOW_SECONDS,
    child_overlap_seconds: int = CHILD_OVERLAP_SECONDS,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    parents: list[dict[str, Any]] = []
    children: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []

    for video_chunks in group_by_video(chunks).values():
        ordered = sorted(video_chunks, key=chunk_start)
        video_parents = build_windows(ordered, parent_window_seconds, parent_overlap_seconds, "parent")
        parents.extend(video_parents)
        for parent in video_parents:
            parent_children = build_children_for_parent(parent, ordered, child_window_seconds, child_overlap_seconds)
            children.extend(parent_children)
            links.extend(to_links(parent, parent_children))

    return parents, children, links


def group_by_video(chunks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for chunk in chunks:
        video_id = (chunk.get("metadata") or {}).get("filename")
        if video_id:
            grouped.setdefault(video_id, []).append(chunk)
    return grouped


def build_windows(chunks: list[dict[str, Any]], window_seconds: int, overlap_seconds: int, kind: str) -> list[dict[str, Any]]:
    if not chunks:
        return []

    video_start = min(chunk_start(chunk) for chunk in chunks)
    video_end = max(chunk_end(chunk) for chunk in chunks)
    stride = window_seconds - overlap_seconds
    windows = []
    start = video_start
    while start < video_end:
        end = min(start + window_seconds, video_end)
        source_chunks = [chunk for chunk in chunks if overlaps(chunk, start, end)]
        if source_chunks:
            windows.append(to_window_chunk(source_chunks, start, end, kind))
        start += stride
    return windows


def build_children_for_parent(
    parent: dict[str, Any],
    video_chunks: list[dict[str, Any]],
    child_window_seconds: int,
    child_overlap_seconds: int,
) -> list[dict[str, Any]]:
    metadata = parent["metadata"]
    start = metadata["start_seconds"]
    end = metadata["end_seconds"]
    stride = child_window_seconds - child_overlap_seconds
    children = []
    child_start = start
    while child_start < end:
        child_end = min(child_start + child_window_seconds, end)
        source_chunks = [chunk for chunk in video_chunks if overlaps(chunk, child_start, child_end)]
        if source_chunks:
            child = to_window_chunk(source_chunks, child_start, child_end, "child")
            child["metadata"]["parent_chunk_id"] = metadata["chunk_id"]
            child["metadata"]["parent_start_timestamp"] = metadata["start_timestamp"]
            child["metadata"]["parent_end_timestamp"] = metadata["end_timestamp"]
            children.append(child)
        child_start += stride
    return children


def to_window_chunk(chunks: list[dict[str, Any]], start: int, end: int, kind: str) -> dict[str, Any]:
    base_metadata = dict(chunks[0].get("metadata") or {})
    video_id = base_metadata["filename"]
    base_metadata.update(
        {
            "chunk_id": f"{video_id}_{kind}_{start}_{end}",
            "start_timestamp": seconds_to_timestamp(start),
            "end_timestamp": seconds_to_timestamp(end),
            "start_seconds": start,
            "end_seconds": end,
            "chunk_strategy": STRATEGY_ID,
            "chunk_role": kind,
        }
    )
    return {
        "page_content": "\n".join(chunk.get("page_content", "").strip() for chunk in chunks if chunk.get("page_content")),
        "metadata": base_metadata,
    }


def to_links(parent: dict[str, Any], children: list[dict[str, Any]]) -> list[dict[str, Any]]:
    parent_metadata = parent["metadata"]
    links = []
    for child in children:
        child_metadata = child["metadata"]
        links.append(
            {
                "child_chunk_id": child_metadata["chunk_id"],
                "parent_chunk_id": parent_metadata["chunk_id"],
                "video_id": child_metadata["filename"],
                "child_start_seconds": child_metadata["start_seconds"],
                "child_end_seconds": child_metadata["end_seconds"],
                "parent_start_seconds": parent_metadata["start_seconds"],
                "parent_end_seconds": parent_metadata["end_seconds"],
            }
        )
    return links


def validate_child_parent_links(
    parents: list[dict[str, Any]],
    children: list[dict[str, Any]],
    links: list[dict[str, Any]],
) -> list[str]:
    parent_by_id = {parent["metadata"].get("chunk_id"): parent for parent in parents}
    child_by_id = {child["metadata"].get("chunk_id"): child for child in children}
    errors = []

    if len(links) != len(children):
        errors.append("link_count_mismatch")

    for child in children:
        child_metadata = child["metadata"]
        parent_id = child_metadata.get("parent_chunk_id")
        parent = parent_by_id.get(parent_id)
        if not parent:
            errors.append(f"orphan_child:{child_metadata.get('chunk_id')}")
            continue
        parent_metadata = parent["metadata"]
        if not (parent_metadata["start_seconds"] <= child_metadata["start_seconds"] <= child_metadata["end_seconds"] <= parent_metadata["end_seconds"]):
            errors.append(f"out_of_parent_range:{child_metadata.get('chunk_id')}")

    for link in links:
        if link["child_chunk_id"] not in child_by_id:
            errors.append(f"missing_child_link:{link['child_chunk_id']}")
        if link["parent_chunk_id"] not in parent_by_id:
            errors.append(f"missing_parent_link:{link['parent_chunk_id']}")

    return errors


def overlaps(chunk: dict[str, Any], start: int, end: int) -> bool:
    return chunk_start(chunk) < end and chunk_end(chunk) > start


def chunk_start(chunk: dict[str, Any]) -> int:
    metadata = chunk.get("metadata") or {}
    return int(metadata.get("start_seconds") or timestamp_to_seconds(metadata.get("start_timestamp")))


def chunk_end(chunk: dict[str, Any]) -> int:
    metadata = chunk.get("metadata") or {}
    return int(metadata.get("end_seconds") or timestamp_to_seconds(metadata.get("end_timestamp")))


def seconds_to_timestamp(value: int) -> str:
    hours, remainder = divmod(value, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate parent_child_180s_45s chunk assets.")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target-dir", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()

    stats = generate_strategy(args.source_dir, args.target_dir)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
