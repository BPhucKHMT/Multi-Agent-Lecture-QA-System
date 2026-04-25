"""FastAPI entry point cho Backend service."""

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
    """Startup và Shutdown events."""
    # Startup: tạo tables nếu chưa có (chỉ dùng trong dev — prod dùng Alembic)
    logger.info(" ============== Backend starting up...")
    logger.info(f"DEBUG: DATABASE_URL is {settings.DATABASE_URL}")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables ready.")

    # Prewarm RAG resources (Embeddings, VectorDB, Reranker) in background
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

    # Không dùng await ở đây để nó chạy ngầm
    import asyncio

    asyncio.create_task(_prewarm())

    yield
    # Shutdown
    logger.info("🔴 Backend shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS — cho phép frontend Vite (5173) và production URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": settings.APP_VERSION}
