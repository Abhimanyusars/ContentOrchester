"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI

from app import __version__
from app.api.routes import briefs, content, health, ws
from app.config import get_settings
from app.database import close_db, init_db
from app.middleware.cors import VercelCORSMiddleware

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle hooks."""
    try:
        logger.info("app_starting", version=__version__)
        await init_db()
        yield
    except Exception as exc:
        logger.error("app_startup_failed", error=str(exc))
        raise
    finally:
        try:
            await close_db()
            from app.redis_client import close_redis
            await close_redis()
            logger.info("app_shutdown_complete")
        except Exception as exc:
            logger.error("app_shutdown_failed", error=str(exc))


def create_app() -> FastAPI:
    """Application factory."""
    try:
        settings = get_settings()
        app = FastAPI(
            title=settings.app_name,
            version=__version__,
            description="Multi-agent AI content creation system",
            lifespan=lifespan,
        )

        app.add_middleware(VercelCORSMiddleware)

        app.include_router(health.router, prefix=settings.api_prefix)
        app.include_router(content.router, prefix=settings.api_prefix)
        app.include_router(briefs.router)
        app.include_router(ws.router)

        @app.get("/")
        async def root() -> dict[str, str]:
            """Landing page when visiting the API base URL."""
            return {
                "name": settings.app_name,
                "version": __version__,
                "status": "running",
                "health": f"{settings.api_prefix}/health",
                "docs": "/docs",
            }

        return app
    except Exception as exc:
        logger.error("app_creation_failed", error=str(exc))
        raise RuntimeError(f"Failed to create app: {exc}") from exc


app = create_app()
