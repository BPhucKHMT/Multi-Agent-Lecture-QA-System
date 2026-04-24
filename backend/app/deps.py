"""FastAPI dependencies — get_current_user, get_admin_user, get_db, get_redis."""
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session
import redis as redis_lib

from backend.app.core.security import decode_token
from backend.app.db.session import get_db
from backend.app.db.redis import get_redis, is_jti_blacklisted
from backend.app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_redis_dep() -> redis_lib.Redis:
    """FastAPI dependency cho Redis client."""
    return get_redis()


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    redis: redis_lib.Redis = Depends(get_redis_dep),
) -> User:
    """Xác thực Access Token và trả về user hiện tại. Hỗ trợ bypass khi chưa có login."""
    
    if not token:
        # Trả về user mặc định để test RAG khi chưa có login flow hoàn thiện
        user = db.query(User).filter(User.username == "admin").first()
        if not user:
            # Tạo user admin giả nếu chưa có
            from backend.app.core.security import get_password_hash
            user = User(
                email="admin@example.com",
                username="admin",
                password_hash=get_password_hash("admin"),
                role="admin"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exc
        email: str = payload.get("sub")
        jti: str = payload.get("jti")
        if not email or not jti:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    # Kiểm tra JTI có trong blacklist không (đã logout / bị revoke)
    if is_jti_blacklisted(redis, jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
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
