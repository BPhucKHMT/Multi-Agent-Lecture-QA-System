"""Config dùng chung cho toàn bộ mã trong src."""

from __future__ import annotations

import os
from typing import Any


def get_env(name: str, default: Any = None) -> Any:
    """Đọc biến môi trường theo key, trả về default nếu không tồn tại."""
    return os.getenv(name, default)


def get_path(name: str) -> str:
    """Trả về đường dẫn runtime theo key, cho phép override bằng env vars."""
    defaults = {
        "data_dir": "artifacts/data",
        "chunks_dir": "artifacts/chunks",
        "vector_db_dir": "artifacts/database_semantic",
        "videos_dir": "artifacts/videos",
        "saved_conversations_dir": "artifacts/saved_conversations",
        "data_extraction_dir": "artifacts/data_extraction",
    }
    env_map = {
        "data_dir": "PUQ_DATA_DIR",
        "chunks_dir": "PUQ_CHUNKS_DIR",
        "vector_db_dir": "PUQ_VECTOR_DB_DIR",
        "videos_dir": "PUQ_VIDEOS_DIR",
        "saved_conversations_dir": "PUQ_SAVED_CONVERSATIONS_DIR",
        "data_extraction_dir": "PUQ_DATA_EXTRACTION_DIR",
    }
    if name not in defaults:
        raise KeyError(f"Unknown runtime path key: {name}")
    return os.getenv(env_map[name], defaults[name])

