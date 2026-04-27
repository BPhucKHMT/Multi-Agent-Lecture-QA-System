import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.api.schemas import ChatRequest, ChatResponse, VideoListResponse, VideoSummaryRequest, VideoSummaryResponse
from src.api.services.chat_service import process_chat, generate_stream, list_local_videos
from src.api.services.summary_service import summarize_with_llm


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def root():
    return {"message": "PUQ Q&A Backend API", "status": "running"}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """API chat chính: gọi RAG và cập nhật hội thoại in-memory."""
    try:
        return process_chat(request)
    except Exception as error:
        logger.error(f"Chat error: {error}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(error)}") from error


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming SSE endpoint: text tokens realtime + metadata JSON cuối."""
    chat_history = []
    for msg in request.messages:
        content = msg.content
        if isinstance(content, dict):
            content = content.get("text", str(content))
        chat_history.append({"role": msg.role, "content": content})

    return StreamingResponse(
        generate_stream(request.conversation_id, chat_history, request.user_message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )



@router.get("/videos", response_model=VideoListResponse)
async def videos(query: str = "", page: int = 1, page_size: int = 20):
    """Lấy danh sách video local trong artifacts/videos cho Summary Hub."""
    try:
        safe_page = max(1, page)
        safe_page_size = max(1, min(page_size, 100))
        return list_local_videos(query=query, page=safe_page, page_size=safe_page_size)
    except Exception as error:
        logger.error(f"Videos listing error: {error}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Videos listing failed: {str(error)}") from error


@router.post("/videos/summary", response_model=VideoSummaryResponse)
async def video_summary(request: VideoSummaryRequest):
    """Tóm tắt nội dung transcript của một video theo video_id bằng LLM (GPT-4o-mini)."""
    try:
        return await summarize_with_llm(request.video_id)
    except Exception as error:
        logger.error(f"Video summary error: {error}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Video summary failed: {str(error)}") from error
