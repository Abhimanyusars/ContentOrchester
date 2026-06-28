"""Async Redis client for caching and task queue coordination."""

from __future__ import annotations

from typing import Any

import redis.asyncio as aioredis
import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)

_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Create or return the async Redis client."""
    global _redis_client
    try:
        if _redis_client is None:
            settings = get_settings()
            _redis_client = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return _redis_client
    except Exception as exc:
        logger.error("redis_client_init_failed", error=str(exc))
        raise RuntimeError(f"Failed to initialize Redis client: {exc}") from exc


async def close_redis() -> None:
    """Close the Redis connection."""
    global _redis_client
    try:
        if _redis_client is not None:
            await _redis_client.close()
            _redis_client = None
            logger.info("redis_closed")
    except Exception as exc:
        logger.error("redis_close_failed", error=str(exc))
        raise RuntimeError(f"Failed to close Redis: {exc}") from exc


async def health_check_redis() -> dict[str, Any]:
    """Check Redis connectivity."""
    try:
        client = await get_redis()
        pong = await client.ping()
        return {"status": "healthy" if pong else "unhealthy", "redis": "connected"}
    except Exception as exc:
        logger.error("redis_health_check_failed", error=str(exc))
        return {"status": "unhealthy", "redis": str(exc)}
