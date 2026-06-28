from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from experiments.src.time_utils import timestamp_to_seconds


def load_chunks(chunks_dir: Union[str, Path], strategy_id: Optional[str] = None) -> List[Dict[str, Any]]:
    root = Path(chunks_dir)
    chunk_pattern = "**/child_chunks.json" if strategy_id == "parent_child_180s_45s" else f"**/{strategy_id or root.name}_chunks.json"
    documents: list[dict[str, Any]] = []
    for chunk_file in sorted(root.glob(chunk_pattern)):
        course_id = _course_id_from_path(chunk_file.parent.name)
        chunks = json.loads(chunk_file.read_text(encoding="utf-8"))
        for chunk in chunks:
            document = _to_document(chunk, course_id, chunk_file)
            if document:
                documents.append(document)
    return documents


def load_parent_chunks(chunks_dir: Union[str, Path]) -> List[Dict[str, Any]]:
    root = Path(chunks_dir)
    documents: list[dict[str, Any]] = []
    for chunk_file in sorted(root.glob("**/parent_chunks.json")):
        course_id = _course_id_from_path(chunk_file.parent.name)
        chunks = json.loads(chunk_file.read_text(encoding="utf-8"))
        for chunk in chunks:
            document = _to_document(chunk, course_id, chunk_file)
            if document:
                documents.append(document)
    return documents


def _to_document(chunk: Dict[str, Any], course_id: str, source_file: Path) -> Optional[Dict[str, Any]]:
    metadata = dict(chunk.get("metadata") or {})
    video_id = metadata.get("filename")
    if not video_id:
        return None

    start_seconds = timestamp_to_seconds(metadata.get("start_timestamp"))
    end_seconds = timestamp_to_seconds(metadata.get("end_timestamp"))
    if end_seconds <= start_seconds:
        return None

    metadata["start_seconds"] = start_seconds
    metadata["end_seconds"] = end_seconds
    metadata["course_id"] = course_id
    metadata["source_file"] = str(source_file)

    timestamp_doc_id = f"{video_id}_{start_seconds}_{end_seconds}"
    chunk_id = metadata.get("chunk_id")
    doc_id = chunk_id if isinstance(chunk_id, str) and chunk_id else timestamp_doc_id

    return {
        "doc_id": doc_id,
        "text": chunk.get("page_content", ""),
        "metadata": metadata,
    }


def _course_id_from_path(name: str) -> str:
    match = re.search(r"cs\d+", name.lower())
    return match.group(0).upper() if match else name.upper()
