import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.errors import AppException, app_exception_handler
from app.models.database import engine, Base

# Import all SQLAlchemy models so they are registered with Base.metadata
# before create_all is called. Without this import, Base.metadata has no
# tables and create_all emits no DDL.
import app.models.meeting  # noqa: F401

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("meeting_summarizer")

# Initialize database tables on startup (idempotent — safe to call on every restart)
try:
    Base.metadata.create_all(bind=engine)
    logger.info("SQLite database tables initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize SQLite database tables: {e}", exc_info=True)

app = FastAPI(
    title="AI Meeting Summarizer API",
    version="1.0.0"
)

# Configure CORS middleware
origins = [settings.FRONTEND_ORIGIN]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register standardized error handler
app.add_exception_handler(AppException, app_exception_handler)

# Register API routes
from app.api import meetings
app.include_router(meetings.router)

@app.get("/api/health")
async def health_check():
    """Health check endpoint to verify backend status."""
    return {"status": "ok"}
