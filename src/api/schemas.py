from typing import Any, List

from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: Any  # Có thể là text hoặc object response


class ChatRequest(BaseModel):
    conversation_id: str
    messages: List[Message]
    user_message: str


class ChatResponse(BaseModel):
    conversation_id: str
    response: Any
    updated_at: str


class ConversationCreate(BaseModel):
    title: str = "Cuộc trò chuyện mới"


class ConversationResponse(BaseModel):
    id: str
    title: str
    messages: List[Message]
    created_at: str
    updated_at: str


class ConversationListItem(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class VideoItem(BaseModel):
    id: str
    video_id: str = ""
    title: str
    course: str
    file_name: str
    relative_path: str
    file_size_mb: float
    thumbnail_url: str = ""
    video_url: str = ""


class VideoListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    query: str
    videos: List[VideoItem]


class VideoSummaryRequest(BaseModel):
    video_id: str


class VideoSummaryResponse(BaseModel):
    video_id: str
    summary: str
