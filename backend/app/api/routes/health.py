"""Health check endpoints."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter

from app import __version__
from app.config import get_settings
from app.database import health_check_db
from app.redis_client import health_check_redis
from app.schemas.content import HealthResponse
from app.services.llm_client import get_llm_client

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return service health status including DB and Redis."""
    try:
        db_health: dict[str, Any] = await health_check_db()
        settings = get_settings()

        if settings.standalone_mode:
            redis_health = {"status": "skipped", "redis": "standalone mode"}
        else:
            redis_health = await health_check_redis()

        ollama_healthy = await get_llm_client().health_check()
        ollama_health: dict[str, Any] = {
            "status": "healthy" if ollama_healthy else "unhealthy",
            "ollama": "connected" if ollama_healthy else "disconnected",
        }

        all_healthy = (
            db_health.get("status") == "healthy"
            and ollama_health.get("status") == "healthy"
            and (settings.standalone_mode or redis_health.get("status") == "healthy")
        )

        return HealthResponse(
            status="healthy" if all_healthy else "degraded",
            version=__version__,
            services={
                "database": db_health,
                "redis": redis_health,
                "ollama": ollama_health,
            },
        )
    except Exception as exc:
        logger.error("health_check_failed", error=str(exc))
        return HealthResponse(
            status="unhealthy",
            version=__version__,
            services={"error": str(exc)},
        )
