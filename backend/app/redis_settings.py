"""Shared ARQ Redis settings for API and worker."""

from __future__ import annotations

from arq.connections import RedisSettings

from app.config import get_settings


def build_arq_redis_settings() -> RedisSettings:
    """Build Redis settings from env (supports Railway REDIS_URL)."""
    settings = get_settings()
    if settings.redis_url_override:
        return RedisSettings.from_dsn(settings.redis_url_override)
    return RedisSettings(
        host=settings.redis_host,
        port=settings.redis_port,
        database=settings.redis_db,
        password=settings.redis_password,
    )
