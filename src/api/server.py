"""FastAPI backend bootstrap cho RAG Q&A."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import threading

from src.api.router import router as api_router
from src.rag_core import resource_manager

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="PUQ Q&A Backend", version="1.0.0")

# CORS middleware (allow Streamlit frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.on_event("startup")
def prewarm_rag_resources():
    """Preload tài nguyên RAG nền để không chặn API startup."""

    def _prewarm_task():
        try:
            logging.info("Prewarming RAG resources in background...")
            resource_manager.prewarm_all_resources()
            logging.info("RAG resources are ready.")
        except Exception as error:
            logging.error(f"Background prewarm failed: {error}", exc_info=True)

    threading.Thread(target=_prewarm_task, name="rag-prewarm", daemon=True).start()


# ============ RUN SERVER ============
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
