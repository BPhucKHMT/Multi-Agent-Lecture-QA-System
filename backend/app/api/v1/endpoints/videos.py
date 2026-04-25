"""Endpoints xử lý tóm tắt video."""

from fastapi import APIRouter, Depends, HTTPException

# from sqlalchemy.orm import Session
import redis

from backend.app.api.v1.endpoints.schemas import (
    VideoSummaryRequest,
    VideoSummaryResponse,
    VideoListResponse,
)

# from backend.app.db.session import get_db
from backend.app.db.redis import get_redis
from backend.app.deps import get_current_user
from backend.app.models.user import User
from backend.app.services import summary as summary_service
from backend.app.services import videos as videos_service

router = APIRouter(prefix="/videos", tags=["videos"])


@router.get("", response_model=VideoListResponse)
async def get_videos(
    query: str = "",
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
):
    """
    Lấy danh sách video (Summary Hub).
    """
    return videos_service.list_videos(query=query, page=page, page_size=page_size)


@router.post("/summary", response_model=VideoSummaryResponse)
async def get_video_summary(
    body: VideoSummaryRequest,
    current_user: User = Depends(get_current_user),
    redis_client: redis.Redis = Depends(get_redis),
):
    """
    Lấy tóm tắt bài giảng video (có cache).
    """
    result = await summary_service.summarize_video(
        video_id=body.video_id, redis_client=redis_client
    )
    if "summary" not in result or not result["summary"]:
        raise HTTPException(
            status_code=404, detail="Không thể tạo tóm tắt cho video này."
        )

    return VideoSummaryResponse(video_id=result["video_id"], summary=result["summary"])
