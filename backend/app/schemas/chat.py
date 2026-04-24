"""Pydantic schemas cho Chat, Video và Summary."""
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime


# --- Video Schemas ---

class VideoItem(BaseModel):
    id: str
    title: str
    thumbnail: Optional[str] = None
    url: str
    published_at: Optional[datetime] = None


class VideoListResponse(BaseModel):
    page: int
    page_size: int
    total_pages: int
    query: str
    videos: List[VideoItem]


# --- Summary Schemas ---

class VideoSummaryRequest(BaseModel):
    video_id: str


class VideoSummaryResponse(BaseModel):
    video_id: str
    summary: str


# --- Chat Schemas ---

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    stream: bool = True


class ChatResponse(BaseModel):
    text: str
    session_id: str
    agent_type: str
    metadata: Optional[dict[str, Any]] = None
