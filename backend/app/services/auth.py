"""Auth service — Register, Login, Refresh Token, Logout."""
from datetime import datetime, timedelta, timezone
import uuid

from sqlalchemy.orm import Session
import redis

from backend.app.core.security import (
    verify_password, get_password_hash,
    create_access_token, create_refresh_token, decode_token, hash_token,
)
from backend.app.db.redis import blacklist_jti, is_jti_blacklisted
from backend.app.models.user import User, UserSession, AuditLog
from backend.app.core.config import settings
from fastapi import HTTPException, status
from jose import JWTError


def register_user(db: Session, email: str, username: str, password: str) -> User:
    """Tạo tài khoản mới. Raise 409 nếu email/username đã tồn tại."""
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email đã được đăng ký")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username đã được sử dụng")

    user = User(
        email=email,
        username=username,
        password_hash=get_password_hash(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_user(
    db: Session,
    redis_client: redis.Redis,
    email: str,
    password: str,
    device_id: str = "unknown",
    user_agent: str = None,
    ip_address: str = None,
) -> tuple[str, str]:
    """
    Xác thực thông tin đăng nhập, tạo JWT Access + Refresh token.
    Trả về (access_token, refresh_token).
    """
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không đúng",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị vô hiệu hóa")

    # Tạo session mới với token_family_id mới
    family_id = uuid.uuid4()
    session_id = uuid.uuid4()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    refresh_token, _ = create_refresh_token(str(user.email), str(session_id), str(family_id))
    access_token = create_access_token(user.email)

    session = UserSession(
        id=session_id,
        user_id=user.id,
        device_id=device_id,
        user_agent=user_agent,
        ip_address=ip_address,
        refresh_token_hash=hash_token(refresh_token),
        token_family_id=family_id,
        expires_at=expire,
    )
    db.add(session)

    # Cập nhật last_login_at
    user.last_login_at = datetime.now(timezone.utc)

    # Audit log
    db.add(AuditLog(user_id=user.id, action="login", metadata_json={"ip": ip_address}))
    db.commit()

    return access_token, refresh_token


def rotate_refresh_token(
    db: Session,
    redis_client: redis.Redis,
    old_refresh_token: str,
) -> tuple[str, str]:
    """
    JWT Rotation với Reuse Detection.
    Trả về (new_access_token, new_refresh_token).
    """
    invalid_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token không hợp lệ hoặc đã hết hạn",
    )
    try:
        payload = decode_token(old_refresh_token)
        if payload.get("type") != "refresh":
            raise invalid_exc
        old_jti = payload["jti"]
        sid = payload["sid"]
        email = payload["sub"]
    except (JWTError, KeyError):
        raise invalid_exc

    # Kiểm tra JTI trong blacklist Redis (đã dùng rồi)
    if is_jti_blacklisted(redis_client, old_jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token đã được sử dụng — có thể đang bị tấn công",
        )

    # Truy vấn session theo ID
    session = db.query(UserSession).filter(UserSession.id == sid).first()

    # Reuse Detection: hash không khớp → token cũ bị dùng lại
    if not session or hash_token(old_refresh_token) != session.refresh_token_hash:
        if session:
            # Thu hồi toàn bộ token trong cùng family
            _revoke_family(db, session.token_family_id)
            db.add(AuditLog(
                user_id=session.user_id,
                action="reuse_detected",
                metadata_json={"family_id": str(session.token_family_id)},
            ))
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phát hiện Refresh Token bị dùng lại — đã đăng xuất khỏi tất cả thiết bị",
        )

    # Tạo cặp token mới
    new_access_token = create_access_token(email)
    new_refresh_token, _ = create_refresh_token(email, sid, str(session.token_family_id))

    # Cập nhật hash trong DB
    session.refresh_token_hash = hash_token(new_refresh_token)
    session.expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db.commit()

    # Đưa JTI cũ vào Redis blacklist (TTL = thời gian còn lại của access token)
    ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    blacklist_jti(redis_client, old_jti, ttl)

    return new_access_token, new_refresh_token


def logout_user(
    db: Session,
    redis_client: redis.Redis,
    access_jti: str,
    user_id: uuid.UUID,
) -> None:
    """Đăng xuất — blacklist access JTI và xóa session."""
    ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    blacklist_jti(redis_client, access_jti, ttl)
    db.add(AuditLog(user_id=user_id, action="logout"))
    db.commit()


def _revoke_family(db: Session, family_id: uuid.UUID) -> None:
    """Thu hồi toàn bộ sessions thuộc cùng token_family_id."""
    now = datetime.now(timezone.utc)
    sessions = db.query(UserSession).filter(
        UserSession.token_family_id == family_id,
        UserSession.revoked_at.is_(None),
    ).all()
    for s in sessions:
        s.revoked_at = now
