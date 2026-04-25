"""
Service quản lý danh sách video từ artifacts.
"""

import json as json_lib
import logging
import os
import re
import unicodedata
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi"}

_VIDEO_ID_NAMESPACE = uuid.UUID("f3f5771b-ec86-4f13-9ef2-8f8ca7617d58")


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_text.lower()).strip()


def _normalize_video_title(stem: str) -> str:
    cleaned = re.sub(r"\.f\d+$", "", stem, flags=re.IGNORECASE)
    cleaned = re.sub(r"^\d+\s*-\s*", "", cleaned)
    return cleaned.strip()


def _stable_video_uuid(key: str) -> uuid.UUID:
    """Sinh UUID ổn định từ khóa nội bộ để khớp schema response."""
    return uuid.uuid5(_VIDEO_ID_NAMESPACE, key)


def _optional_url(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None


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
            if not title:
                continue
            normalized_title = _normalize_text(_normalize_video_title(title))
            if not normalized_title:
                continue
            key = f"{course_name.lower()}::{normalized_title}"
            mapping[key] = {
                "video_url": video_url,
                "video_id": video_id,
                "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                if video_id
                else "",
            }
    return mapping


@lru_cache(maxsize=1)
def _build_video_index() -> List[Dict[str, Any]]:
    videos_dir = os.getenv("PUQ_VIDEOS_DIR", "artifacts/videos")
    videos_root = Path(videos_dir)
    if not videos_root.exists() or not videos_root.is_dir():
        logger.warning(f"Thư mục videos không tồn tại: {videos_root}")
        return []

    deduped: Dict[str, Dict[str, Any]] = {}

    # Chế độ chỉ đọc từ metadata.json (Không quét file vật lý để tiết kiệm tài nguyên)
    for metadata_file in videos_root.glob("*/metadata.json"):
        course_name = metadata_file.parent.name
        try:
            payload = json_lib.loads(metadata_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Lỗi đọc metadata tại {metadata_file}: {e}")
            continue

        for video in payload.get("videos", []):
            title = str(video.get("title", "")).strip()
            video_id = str(video.get("video_id", "")).strip()
            video_url = str(video.get("url", "")).strip()
            if not title:
                continue

            normalized_title = _normalize_video_title(title)
            # Khóa duy nhất để tránh trùng lặp: course::title
            dedupe_key = f"{course_name.lower()}::{_normalize_text(normalized_title)}"
            stable_id = _stable_video_uuid(dedupe_key)
            thumbnail_url = (
                f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" if video_id else ""
            )

            deduped[dedupe_key] = {
                "id": stable_id,
                "video_id": video_id or None,
                "title": normalized_title,
                "course": course_name or None,
                "thumbnail_url": _optional_url(thumbnail_url),
                "video_url": _optional_url(video_url),
                "file_name": None,  # Không dùng file local
                "relative_path": None,
                "file_size_mb": None,
                "_search_key": _normalize_text(
                    f"{normalized_title} {course_name} {video_id}"
                ),
            }

    return sorted(
        deduped.values(),
        key=lambda item: (item["course"].lower(), item["title"].lower()),
    )


def list_videos(query: str = "", page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    all_videos = _build_video_index()
    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, 100))

    if not all_videos:
        return {
            "total": 0,
            "page": safe_page,
            "page_size": safe_page_size,
            "total_pages": 0,
            "query": query,
            "videos": [],
        }

    query_text = _normalize_text(query)
    if query_text:
        all_videos = [v for v in all_videos if query_text in v.get("_search_key", "")]

    total = len(all_videos)
    total_pages = (total + safe_page_size - 1) // safe_page_size if total > 0 else 0

    if total_pages > 0 and safe_page > total_pages:
        safe_page = total_pages

    start_index = (safe_page - 1) * safe_page_size
    page_items = all_videos[start_index : start_index + safe_page_size]

    return {
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
        "total_pages": total_pages,
        "query": query,
        "videos": [
            {k: v for k, v in item.items() if not k.startswith("_")}
            for item in page_items
        ],
    }
