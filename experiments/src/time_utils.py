from __future__ import annotations

from typing import Union


def timestamp_to_seconds(timestamp: Union[str, int, float, None]) -> int:
    if timestamp in (None, ""):
        return 0
    if isinstance(timestamp, (int, float)):
        return int(timestamp)

    parts = [int(part) for part in str(timestamp).strip().split(":")]
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return hours * 3600 + minutes * 60 + seconds
    if len(parts) == 2:
        minutes, seconds = parts
        return minutes * 60 + seconds
    return parts[0]
