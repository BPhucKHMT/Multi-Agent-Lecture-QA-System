"""Placeholder logging dùng chung cho giai đoạn WS1.

Giữ cấu hình đơn giản để tương thích ngược, không ép thay đổi cấu hình cũ.
"""

from __future__ import annotations

import logging


def get_logger(name: str) -> logging.Logger:
    """Trả logger theo tên, dùng cấu hình hiện có của ứng dụng."""
    return logging.getLogger(name)

