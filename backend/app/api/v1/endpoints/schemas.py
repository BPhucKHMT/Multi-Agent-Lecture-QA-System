"""Pydantic schemas cho Backend (Auth, Chat, Video, Summary)."""
from pydantic import BaseModel, EmailStr, field_validator, Field
import uuid
from datetime import datetime
from typing import List, Optional, Any


# --- Auth Schemas ---

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace("_", "").isalnum():
            raise ValueError("Username chỉ được chứa chữ cái, số và dấu gạch dưới")
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Username phải từ 3 đến 50 ký tự")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Mật khẩu phải có ít nhất 8 ký tự")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Video Schemas ---

class VideoItem(BaseModel):
    id: str
    video_id: str = ""
    title: str
    course: str = ""
    file_name: str = ""
    relative_path: str = ""
    file_size_mb: float = 0.0
    thumbnail_url: str = ""
    video_url: str = ""
    published_at: Optional[datetime] = None


class VideoListResponse(BaseModel):
    total: int
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
    user_message: str
    conversation_id: Optional[str] = None
    stream: bool = True


class ChatResponse(BaseModel):
    text: str
    session_id: str
    agent_type: str
    metadata: Optional[dict[str, Any]] = None
