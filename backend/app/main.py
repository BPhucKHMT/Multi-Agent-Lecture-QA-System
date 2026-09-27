"""FastAPI entry point cho backend service.

Module này cấu hình application lifecycle, CORS, router API v1 và health check.
Trong giai đoạn startup, backend tạo bảng DB cho môi trường dev, prewarm RAG
resources và prewarm Redis semantic cache ở background để request đầu tiên không
phải gánh toàn bộ chi phí khởi tạo model/vector DB.
"""

import warnings
warnings.filterwarnings("ignore")

from contextlib import asynccontextmanager
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import start_http_server

from backend.app.core.config import settings
from backend.app.api.v1.router import router as api_v1_router
from backend.app.db.session import engine
from backend.app.models.user import Base
from src.shared import metrics as _metrics
from src.shared.observability import initialize_langfuse, shutdown_langfuse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _start_metrics_exporter():
    """Khởi động exporter nội bộ khi được bật qua biến môi trường."""
    if os.getenv("PUQ_METRICS_ENABLED", "").strip().lower() != "true":
        return None, None

    port = int(os.getenv("PUQ_METRICS_PORT", "9102"))
    bind_host = os.getenv("PUQ_METRICS_BIND_HOST", "127.0.0.1")
    logger.info("📊 Metrics exporter listening on %s:%s", bind_host, port)
    server, thread = start_http_server(port=port, addr=bind_host)
    return server, thread


def _stop_metrics_exporter(server, thread):
    """Dừng exporter và chờ thread phục vụ kết thúc."""
    try:
        if server is not None:
            server.shutdown()
    finally:
        try:
            if server is not None:
                server.server_close()
        finally:
            if thread is not None:
                thread.join()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Quản lý vòng đời backend: startup prewarm và shutdown logging.

    Các tác vụ nặng được chạy trong background/threadpool để không block event
    loop chính của FastAPI. Nếu Redis/RAG prewarm lỗi, backend vẫn tiếp tục chạy
    và log nguyên nhân để người vận hành kiểm tra sau.
    """
    metrics_server = metrics_thread = None
    close_jev_http_client = None

    try:
        metrics_server, metrics_thread = _start_metrics_exporter()
        initialize_langfuse()

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

        from src.generation.jev_router import (
            close_jev_http_client as close_jev_client,
            open_jev_http_client,
        )

        close_jev_http_client = close_jev_client
        open_jev_http_client()
        yield
    finally:
        try:
            _stop_metrics_exporter(metrics_server, metrics_thread)
        finally:
            try:
                shutdown_langfuse()
            finally:
                try:
                    if close_jev_http_client is not None:
                        await close_jev_http_client()
                finally:
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
