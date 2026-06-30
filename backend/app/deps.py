"""FastAPI dependencies — get_current_user, get_admin_user, get_db, get_redis."""

from datetime import datetime, timezone
import time
from typing import Optional
import uuid
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session
import redis as redis_lib

from backend.app.core.security import decode_token
from backend.app.db.session import get_db
from backend.app.db.redis import get_redis, is_jti_blacklisted
from backend.app.models.user import User, UserSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_redis_dep() -> redis_lib.Redis:
    """FastAPI dependency cho Redis client."""
    return get_redis()


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    redis: redis_lib.Redis = Depends(get_redis_dep),
) -> User:
    """
    Xác thực Access Token và trả về user hiện tại.
    Bắt buộc có Access Token hợp lệ.
    """

    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exc
        email: str = payload.get("sub")
        jti: str = payload.get("jti")
        sid: str = payload.get("sid")
        if not email or not jti or not sid:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    # Kiểm tra JTI có trong blacklist không (đã logout / bị revoke)
    if is_jti_blacklisted(redis, jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    session = db.query(UserSession).filter(UserSession.id == sid).first()
    if (
        session is None
        or session.revoked_at is not None
        or session.expires_at <= datetime.now(timezone.utc)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is no longer active",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active or user.id != session.user_id:
        raise credentials_exc
    return user


async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Chỉ cho phép admin truy cập."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


async def limit_chat_rate(
    request: Request,
    redis_client: redis_lib.Redis = Depends(get_redis_dep),
) -> None:
    """
    Dependency giới hạn tần suất chat của user theo địa chỉ IP (10 requests / 10 phút).
    Sử dụng thuật toán Sliding Window qua Redis Sorted Set.
    """
    # 1. Lấy địa chỉ IP thực tế của client (hỗ trợ Nginx / Cloudflare proxy)
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        client_ip = x_forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.headers.get("x-real-ip") or (request.client.host if request.client else "127.0.0.1")
        
    # Key định danh giới hạn chat cho IP này
    key = f"rate_limit:chat:ip:{client_ip}"
    
    # Giới hạn 10 requests trong 10 phút (600 giây)
    limit = 10
    window_seconds = 600
    
    now = time.time()
    cutoff = now - window_seconds
    member = f"{now}:{uuid.uuid4()}"
    
    try:
        pipe = redis_client.pipeline()
        # 1. Dọn dẹp các request cũ ngoài cửa sổ 10 phút
        pipe.zremrangebyscore(key, 0, cutoff)
        # 2. Thêm request mới vào set
        pipe.zadd(key, {member: now})
        # 3. Đếm số lượng request hiện tại trong 10 phút qua
        pipe.zcard(key)
        # 4. Set TTL cho key để giải phóng bộ nhớ khi không có request mới
        pipe.expire(key, window_seconds)
        
        results = pipe.execute()
        current_count = results[2]
        
        if current_count > limit:
            # Nếu vượt giới hạn, xóa bớt member vừa thêm vào để tránh set phình to không cần thiết
            redis_client.zrem(key, member)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Bạn đã vượt quá giới hạn gửi 10 tin nhắn trong 10 phút. Vui lòng thử lại sau.",
            )
    except redis_lib.RedisError as e:
        # Nếu Redis lỗi, ta log lỗi và cho phép request đi tiếp để không làm gián đoạn dịch vụ
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Redis error during rate limiting check for IP {client_ip}: {e}")
