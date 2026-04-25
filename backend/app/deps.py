"""FastAPI dependencies — get_current_user, get_admin_user, get_db, get_redis."""

from datetime import datetime, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
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
