from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import redis
import uuid

from backend.app.api.v1.endpoints.schemas import ChatRequest # Sẽ cập nhật schemas sau
from backend.app.db.session import get_db
from backend.app.db.redis import get_redis
from backend.app.deps import get_current_user
from backend.app.models.user import User
from backend.app.services import chat as chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/stream")
async def chat_stream(
    body: ChatRequest,
    current_user: User = Depends(get_current_user), # Bạn cần login để lấy token
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    """
    Endpoint streaming hội thoại AI (SSE).
    Yêu cầu: Access Token hợp lệ.
    """
    session_id = body.conversation_id or str(uuid.uuid4())
    
    return StreamingResponse(
        chat_service.generate_chat_stream(
            db=db,
            user_id=current_user.id,
            session_id=session_id,
            user_message=body.user_message,
            redis_client=redis_client
        ),
        media_type="text/event-stream"
    )


@router.get("/history")
def get_history(
    session_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy lịch sử hội thoại của user hiện tại."""
    history = chat_service.get_chat_history(db, current_user.id, session_id)
    return history


@router.get("/sessions")
def get_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy danh sách các phiên hội thoại của user hiện tại."""
    sessions = chat_service.get_chat_sessions(db, current_user.id)
    return sessions
