"""SQLAlchemy engine và session factory."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from backend.app.core.config import settings

# Tạo engine — Supabase yêu cầu SSL, psycopg2 sẽ tự xử lý qua URL
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # Kiểm tra kết nối trước khi dùng
    pool_size=5,
    max_overflow=10,
    echo=settings.DEBUG,      # Log SQL khi DEBUG=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — cấp một DB session cho mỗi request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
