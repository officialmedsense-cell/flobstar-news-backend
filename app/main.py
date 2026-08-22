"""
Flobstar News Intelligence Backend
Main FastAPI application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.database import engine, Base
from app.api import sources_router, stories_router, assignments_router, notifications_router, poller_router
from app.api.ai import router as ai_router
from app.scheduler import scheduler
from app.notifications.telegram import telegram

# Import all models so SQLAlchemy registers them before create_all
import app.models.news_source          # noqa: F401
import app.models.news_story           # noqa: F401
import app.models.source_health_history # noqa: F401
import app.models.story_assignment     # noqa: F401
import app.models.story_status_history # noqa: F401
import app.models.ai_generation        # noqa: F401
import app.models.news_notification    # noqa: F401
import app.models.audit_log            # noqa: F401

# Setup structured logging
setup_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager — startup and shutdown."""
    logger.info("Starting Flobstar News Intelligence Backend")

    # Auto-create database tables (safe — skips existing tables)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified / created")
    except Exception as e:
        logger.error("Database initialization failed", error=str(e))

    # Start background task scheduler
    await scheduler.start()
    logger.info("Background scheduler started (RSS polling every 15 min)")

    # Telegram startup notification
    await telegram.alert_system_status(
        "🚀 Flobstar News Intelligence Backend is now online.\n"
        "RSS polling active · AI: Mistral"
    )

    yield

    # Shutdown
    logger.info("Shutting down Flobstar News Intelligence Backend")
    await scheduler.stop()
    await engine.dispose()
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Flobstar News Intelligence API",
    description="Backend API for Flobstar News Intelligence & Automated Newsroom",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — use configured frontend URL (not wildcard in production)
allowed_origins = [settings.FRONTEND_URL]
if settings.DEBUG:
    # Allow all localhost ports during development
    allowed_origins += [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────
# Health check
# ─────────────────────────────────────────

@app.get("/health", tags=["system"])
async def health_check():
    """
    Health check endpoint.
    Also serves as the Render/UptimeRobot keep-alive ping target.
    Returns 200 OK with service status to prevent Render free-tier sleep.
    """
    from app.services.ai_generator import ai_generator
    from datetime import datetime, timezone
    return {
        "status": "healthy",
        "service": "Flobstar News Intelligence Backend",
        "version": "1.0.0",
        "server_time_utc": datetime.now(timezone.utc).isoformat(),
        "scheduler": {
            "running": scheduler.running,
            "interval_minutes": settings.RSS_POLLING_INTERVAL_MINUTES,
        },
        "ai": {
            "default_provider": ai_generator.get_default_provider(),
            "mistral": ai_generator.is_available("mistral"),
            "openai": ai_generator.is_available("openai"),
            "anthropic": ai_generator.is_available("anthropic"),
        },
        "telegram": {
            "enabled": telegram.enabled,
        },
    }


# ─────────────────────────────────────────
# Routers
# ─────────────────────────────────────────

app.include_router(sources_router,      prefix="/api/v1/sources",       tags=["sources"])
app.include_router(stories_router,      prefix="/api/v1/stories",       tags=["stories"])
app.include_router(assignments_router,  prefix="/api/v1/assignments",   tags=["assignments"])
app.include_router(notifications_router,prefix="/api/v1/notifications", tags=["notifications"])
app.include_router(ai_router,           prefix="/api/v1/ai",            tags=["ai"])
app.include_router(poller_router,       prefix="/api/v1/poller",        tags=["poller"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )
