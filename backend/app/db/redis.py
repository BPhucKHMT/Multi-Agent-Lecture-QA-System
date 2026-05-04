"""Redis client factory cho backend.

Module này cung cấp hai singleton Redis client có mục đích khác nhau:
- `get_redis()`: client text (`decode_responses=True`) cho auth, blacklist,
  rate limit và các key/value string thông thường.
- `get_redis_binary()`: client bytes (`decode_responses=False`) cho Redis Stack
  semantic cache vì vector embedding được lưu dạng binary.

Tách hai client giúp tránh lỗi decode bytes embedding thành UTF-8 khi dùng
RediSearch vector index.
"""

from typing import Optional
import redis
from backend.app.core.config import settings

# Upstash dùng giao thức rediss:// (SSL), redis-py hỗ trợ sẵn
_redis_client: Optional[redis.Redis] = None
_redis_binary_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    """Trả singleton Redis text client cho các nghiệp vụ key/value thông thường."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
        )
    return _redis_client


def get_redis_binary() -> redis.Redis:
    """Trả singleton Redis bytes client cho Redis Stack vector cache."""
    global _redis_binary_client
    if _redis_binary_client is None:
        _redis_binary_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=False,
            socket_timeout=5,
            socket_connect_timeout=5,
        )
    return _redis_binary_client


# --- Helpers ---
def blacklist_jti(redis_client: redis.Redis, jti: str, ttl_seconds: int) -> None:
    """Đưa JWT ID vào blacklist cho đến khi token hết hạn.

    Dùng khi logout hoặc revoke token để access token còn hạn không thể tiếp tục
    được sử dụng. TTL phải khớp thời gian sống còn lại của token.
    """
    redis_client.setex(f"auth:revoked_jti:{jti}", ttl_seconds, "1")


def is_jti_blacklisted(redis_client: redis.Redis, jti: str) -> bool:
    """Kiểm tra JTI có trong blacklist không."""
    return redis_client.exists(f"auth:revoked_jti:{jti}") == 1


def check_rate_limit(
    redis_client: redis.Redis, key: str, limit: int, window_seconds: int
) -> bool:
    """Kiểm tra key có vượt giới hạn request trong cửa sổ thời gian không.

    Trả `True` khi đã vượt giới hạn, `False` khi request vẫn được phép đi tiếp.
    Dùng Redis `INCR` + `EXPIRE` để giữ counter đơn giản và tự hết hạn.
    """
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, window_seconds)
    return count > limit
