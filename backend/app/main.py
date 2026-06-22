"""FastAPI entry point cho backend service.

Module này cấu hình application lifecycle, CORS, router API v1 và health check.
Trong giai đoạn startup, backend tạo bảng DB cho môi trường dev, prewarm RAG
resources và prewarm Redis semantic cache ở background để request đầu tiên không
phải gánh toàn bộ chi phí khởi tạo model/vector DB.
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.api.v1.router import router as api_v1_router
from backend.app.db.session import engine
from backend.app.models.user import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Quản lý vòng đời backend: startup prewarm và shutdown logging.

    Các tác vụ nặng được chạy trong background/threadpool để không block event
    loop chính của FastAPI. Nếu Redis/RAG prewarm lỗi, backend vẫn tiếp tục chạy
    và log nguyên nhân để người vận hành kiểm tra sau.
    """
    # Tạo bảng trong dev; production nên quản lý schema bằng Alembic migration.
    logger.info(" ============== Backend starting up...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables ready.")

    # Prewarm RAG resources trong background để không block FastAPI startup.
    import anyio

    async def _prewarm():
        try:
            from src.rag_core.resource_manager import prewarm_all_resources

            logger.info("🧠 Prewarming RAG resources in background...")
            # Chạy hàm đồng bộ trong threadpool để không block event loop
            await anyio.to_thread.run_sync(prewarm_all_resources)
            logger.info("✅ RAG resources ready.")
        except Exception as e:
            logger.error(f"❌ Failed to prewarm RAG resources: {e}")
            logger.exception("❌ Prewarm traceback")

    # Không await để prewarm chạy nền; request vẫn có thể vào backend ngay.
    import asyncio

    asyncio.create_task(_prewarm())

    async def _prewarm_semantic_cache():
        """Load các cặp Q/A gần nhất từ PostgreSQL sang Redis semantic cache."""
        if not settings.SEMANTIC_CACHE_ENABLED or not settings.SEMANTIC_CACHE_PREWARM_ENABLED:
            return
        try:
            from backend.app.core.cache.prewarm import prewarm_semantic_cache
            from backend.app.core.cache.semantic import SemanticCache
            from backend.app.db.redis import get_redis_binary
            from backend.app.db.session import SessionLocal

            def _run_prewarm() -> int:
                db = SessionLocal()
                try:
                    cache = SemanticCache(get_redis_binary())
                    return prewarm_semantic_cache(
                        db,
                        cache,
                        settings.SEMANTIC_CACHE_PREWARM_LIMIT,
                    )
                finally:
                    db.close()

            indexed = await anyio.to_thread.run_sync(_run_prewarm)
            logger.info("✅ Redis semantic cache prewarmed: %s items.", indexed)
        except Exception as e:
            logger.warning("⚠️ Redis semantic cache prewarm skipped: %s", e)

    asyncio.create_task(_prewarm_semantic_cache())

    yield
    # Shutdown
    logger.info("🔴 Backend shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS — cho phép tất cả origins trong dev (dùng "*" thì không được kết hợp credentials)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=False,  # ← Phải False khi dùng "*" (dev mode)
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": settings.APP_VERSION}
