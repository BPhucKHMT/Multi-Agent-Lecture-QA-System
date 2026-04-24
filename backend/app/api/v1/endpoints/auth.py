"""Auth endpoints — /register, /login, /refresh, /logout, /me."""
from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import redis

from backend.app.api.v1.endpoints.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, RefreshRequest, UserResponse,
)
from backend.app.db.session import get_db
from backend.app.db.redis import get_redis
from backend.app.deps import get_current_user, oauth2_scheme
from backend.app.models.user import User
from backend.app.services import auth as auth_service
from backend.app.core.security import decode_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterRequest,
    db: Session = Depends(get_db),
):
    """Đăng ký tài khoản mới."""
    user = auth_service.register_user(db, body.email, body.username, body.password)
    return user


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    """Đăng nhập — trả về Access Token và Refresh Token."""
    access_token, refresh_token = auth_service.login_user(
        db=db,
        redis_client=redis_client,
        email=body.email,
        password=body.password,
        device_id=request.headers.get("X-Device-ID", "web"),
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    body: RefreshRequest,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    """Xoay vòng Refresh Token — JWT Rotation với Reuse Detection."""
    access_token, refresh_token = auth_service.rotate_refresh_token(
        db=db,
        redis_client=redis_client,
        old_refresh_token=body.refresh_token,
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    token: str = Depends(oauth2_scheme),
):
    """Đăng xuất — blacklist Access Token hiện tại."""
    payload = decode_token(token)
    auth_service.logout_user(db, redis_client, payload["jti"], current_user.id)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    """Lấy thông tin user hiện tại."""
    return current_user
