"""API v1 router — gộp tất cả endpoints."""
from fastapi import APIRouter

from backend.app.api.v1.endpoints import auth, chat, videos

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(chat.router)
router.include_router(videos.router)
