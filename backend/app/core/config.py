"""Cấu hình ứng dụng backend — đọc từ file .env."""
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings


env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "PUQ Q&A Backend"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    # --- Database ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # --- Redis ---
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    SEMANTIC_CACHE_ENABLED: bool = os.getenv("SEMANTIC_CACHE_ENABLED", "True").lower() == "true"
    SEMANTIC_CACHE_BACKEND: str = os.getenv("SEMANTIC_CACHE_BACKEND", "redis_stack")
    SEMANTIC_CACHE_EMBEDDING_MODEL: str = os.getenv(
        "SEMANTIC_CACHE_EMBEDDING_MODEL", "text-embedding-3-small"
    )
    SEMANTIC_CACHE_VECTOR_DIM: int = int(os.getenv("SEMANTIC_CACHE_VECTOR_DIM", "1536"))
    SEMANTIC_CACHE_TOP_K: int = int(os.getenv("SEMANTIC_CACHE_TOP_K", "5"))
    SEMANTIC_CACHE_STRONG_THRESHOLD: float = float(
        os.getenv("SEMANTIC_CACHE_STRONG_THRESHOLD", "0.95")
    )
    SEMANTIC_CACHE_HYBRID_THRESHOLD: float = float(
        os.getenv("SEMANTIC_CACHE_HYBRID_THRESHOLD", "0.90")
    )
    SEMANTIC_CACHE_KEYWORD_OVERLAP: float = float(
        os.getenv("SEMANTIC_CACHE_KEYWORD_OVERLAP", "0.55")
    )
    SEMANTIC_CACHE_TTL_SECONDS: int = int(os.getenv("SEMANTIC_CACHE_TTL_SECONDS", "86400"))
    SEMANTIC_CACHE_PREWARM_ENABLED: bool = (
        os.getenv("SEMANTIC_CACHE_PREWARM_ENABLED", "True").lower() == "true"
    )
    SEMANTIC_CACHE_PREWARM_LIMIT: int = int(
        os.getenv("SEMANTIC_CACHE_PREWARM_LIMIT", "1000")
    )

    # --- OpenAI ---
    OPENAI_API_KEY: str = os.getenv("myAPIKey", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # --- JWT ---
    JWT_SECRET: str = os.getenv("JWT_SECRET", "changeme")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # --- CORS ---
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
