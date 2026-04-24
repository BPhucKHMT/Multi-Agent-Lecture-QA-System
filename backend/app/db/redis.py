"""Redis client (Upstash compatible) — dùng cho blacklist JTI, rate limit, semantic cache."""
from typing import Optional
import redis
from backend.app.core.config import settings

# Upstash dùng giao thức rediss:// (SSL), redis-py hỗ trợ sẵn
_redis_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    """Trả về singleton Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,  # Trả về str thay vì bytes
            socket_timeout=5,
            socket_connect_timeout=5,
        )
    return _redis_client


# --- Helpers ---

def blacklist_jti(redis_client: redis.Redis, jti: str, ttl_seconds: int) -> None:
    """Đưa JTI vào blacklist với TTL tương ứng."""
    redis_client.setex(f"auth:revoked_jti:{jti}", ttl_seconds, "1")


def is_jti_blacklisted(redis_client: redis.Redis, jti: str) -> bool:
    """Kiểm tra JTI có trong blacklist không."""
    return redis_client.exists(f"auth:revoked_jti:{jti}") == 1


def check_rate_limit(redis_client: redis.Redis, key: str, limit: int, window_seconds: int) -> bool:
    """
    Trả về True nếu vượt giới hạn, False nếu còn trong giới hạn.
    Dùng INCR + EXPIRE để đếm số lần gọi trong time window.
    """
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, window_seconds)
    return count > limit
