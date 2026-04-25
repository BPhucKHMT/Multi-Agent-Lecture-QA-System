"""Tiện ích bảo mật — sign/verify JWT, hash password."""

from datetime import datetime, timedelta, timezone
from typing import Any, Union
import hashlib
import uuid

from jose import jwt
from passlib.context import CryptContext

from backend.app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


# --- Password ---


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# --- Token ---


def create_access_token(
    subject: Union[str, Any], jti: str = None, sid: str = None
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": jti or str(uuid.uuid4()),
        "type": "access",
    }
    if sid:
        payload["sid"] = str(sid)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: Union[str, Any], sid: str, family_id: str
) -> tuple[str, str]:
    """Trả về (token, jti) để lưu jti vào blacklist sau khi rotate."""
    jti = str(uuid.uuid4())
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": jti,
        "sid": str(sid),
        "fid": str(family_id),
        "type": "refresh",
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return token, jti


def decode_token(token: str) -> dict:
    """Giải mã token. Raise JWTError nếu không hợp lệ."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


def hash_token(token: str) -> str:
    """Tạo SHA-256 hash của token để lưu vào DB (không lưu raw token)."""
    return hashlib.sha256(token.encode()).hexdigest()
