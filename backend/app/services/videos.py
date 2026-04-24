"""
Service quản lý danh sách video từ artifacts.
"""
import json as json_lib
import logging
import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi"}

def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_text.lower()).strip()

def _normalize_video_title(stem: str) -> str:
    cleaned = re.sub(r"\.f\d+$", "", stem, flags=re.IGNORECASE)
    cleaned = re.sub(r"^\d+\s*-\s*", "", cleaned)
    return cleaned.strip()

@lru_cache(maxsize=1)
def _load_video_metadata_map() -> Dict[str, Dict[str, str]]:
    videos_dir = os.getenv("PUQ_VIDEOS_DIR", "artifacts/videos")
    videos_root = Path(videos_dir)
    mapping: Dict[str, Dict[str, str]] = {}
    if not videos_root.exists() or not videos_root.is_dir():
        return mapping

    for metadata_file in videos_root.glob("*/metadata.json"):
        course_name = metadata_file.parent.name
        try:
            payload = json_lib.loads(metadata_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        for video in payload.get("videos", []):
            title = str(video.get("title", "")).strip()
            video_url = str(video.get("url", "")).strip()
            video_id = str(video.get("video_id", "")).strip()
            if not title: continue
            normalized_title = _normalize_text(_normalize_video_title(title))
            if not normalized_title: continue
            key = f"{course_name.lower()}::{normalized_title}"
            mapping[key] = {
                "video_url": video_url,
                "video_id": video_id,
                "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" if video_id else "",
            }
    return mapping

@lru_cache(maxsize=1)
def _build_video_index() -> List[Dict[str, Any]]:
    videos_dir = os.getenv("PUQ_VIDEOS_DIR", "artifacts/videos")
    videos_root = Path(videos_dir)
    if not videos_root.exists() or not videos_root.is_dir():
        return []

    deduped: Dict[str, Dict[str, Any]] = {}

    # Fast path: metadata.json
    for metadata_file in videos_root.glob("*/metadata.json"):
        course_name = metadata_file.parent.name
        try:
            payload = json_lib.loads(metadata_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        for video in payload.get("videos", []):
            title = str(video.get("title", "")).strip()
            video_id = str(video.get("video_id", "")).strip()
            video_url = str(video.get("url", "")).strip()
            if not title: continue
            
            normalized_title = _normalize_video_title(title)
            dedupe_key = f"{course_name.lower()}::{_normalize_text(normalized_title)}"
            
            deduped[dedupe_key] = {
                "id": f"{course_name.lower()}::{video_id or _normalize_text(normalized_title)}",
                "video_id": video_id,
                "title": normalized_title,
                "course": course_name,
                "file_name": f"{video_id}.mp4" if video_id else normalized_title,
                "relative_path": "",
                "file_size_mb": 0.0,
                "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" if video_id else "",
                "video_url": video_url,
                "_search_key": _normalize_text(f"{normalized_title} {course_name} {video_id}"),
                "_source": "metadata"
            }

    # Fallback path: filesystem scan
    metadata_map = _load_video_metadata_map()
    for file_path in videos_root.rglob("*"):
        if not file_path.is_file() or file_path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue

        relative_path = file_path.relative_to(videos_root).as_posix()
        course = relative_path.split("/")[0] if "/" in relative_path else "General"
        normalized_title = _normalize_video_title(file_path.stem)
        dedupe_key = f"{course.lower()}::{_normalize_text(normalized_title)}"
        file_size = file_path.stat().st_size

        if dedupe_key not in deduped or (deduped[dedupe_key].get("_source") != "metadata" and file_size > deduped[dedupe_key].get("_size_bytes", 0)):
             metadata = metadata_map.get(dedupe_key, {})
             deduped[dedupe_key] = {
                "id": dedupe_key,
                "video_id": metadata.get("video_id", ""),
                "title": normalized_title,
                "course": course,
                "file_name": file_path.name,
                "relative_path": relative_path,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "thumbnail_url": metadata.get("thumbnail_url", ""),
                "video_url": metadata.get("video_url", ""),
                "_size_bytes": file_size,
                "_search_key": _normalize_text(f"{normalized_title} {course} {file_path.name}"),
            }

    return sorted(deduped.values(), key=lambda item: (item["course"].lower(), item["title"].lower()))

def list_videos(query: str = "", page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    all_videos = _build_video_index()
    if not all_videos:
        return {"total": 0, "page": 1, "page_size": page_size, "total_pages": 0, "query": query, "videos": []}

    query_text = _normalize_text(query)
    if query_text:
        all_videos = [v for v in all_videos if query_text in v.get("_search_key", "")]

    total = len(all_videos)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    start_index = (page - 1) * page_size
    page_items = all_videos[start_index:start_index + page_size]
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "query": query,
        "videos": [{k: v for k, v in item.items() if not k.startswith("_")} for item in page_items]
    }
