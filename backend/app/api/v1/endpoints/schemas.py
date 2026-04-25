"""
Pydantic schemas cho Backend (Auth, Chat, Video, Summary).
- Bộ khung (blueprint) dùng để định nghĩa cấu trúc dữ liệu
- Kiểm tra tính hợp lệ của dữ liệu và chuyển đổi dữ liệu giữa Client và Server
"""

from pydantic import BaseModel, EmailStr, AnyHttpUrl
from pydantic import field_validator, model_validator
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
        v = v.strip()
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
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


# --- Video Schemas ---


class VideoItem(BaseModel):
    id: uuid.UUID
    video_id: Optional[str] = None
    title: str
    course: Optional[str] = None
    file_name: Optional[str] = None
    relative_path: Optional[str] = None
    file_size_mb: Optional[float] = None
    thumbnail_url: Optional[AnyHttpUrl] = None
    video_url: Optional[AnyHttpUrl] = None
    published_at: Optional[datetime] = None


class VideoListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    query: str
    videos: List[VideoItem]

    @model_validator(mode="after")  # kiểm tra tính nhất quán giữa các field
    def check_pagination(self) -> "VideoListResponse":
        expected = (self.total + self.page_size - 1) // self.page_size
        if self.total_pages != expected:
            raise ValueError("total_pages không khớp total và page_size")
        return self


# --- Summary Schemas ---


class VideoSummaryRequest(BaseModel):
    video_id: str


class VideoSummaryResponse(BaseModel):
    video_id: str
    summary: str


# --- Chat Schemas ---


class ChatRequest(BaseModel):
    """
    - user_message
    - conversation_id
    - stream
    """

    user_message: str
    conversation_id: Optional[str] = None
    stream: bool = False

    @field_validator("user_message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Tin nhắn không được để trống")
        if len(v) > 5000:
            raise ValueError("Tin nhắn quá dài (tối đa 5000 ký tự)")
        return v


class ChatResponse(BaseModel):
    text: str
    session_id: str
    agent_type: str
    metadata: Optional[dict[str, Any]] = None
