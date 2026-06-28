"""Async PostgreSQL database engine and session management."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

logger = structlog.get_logger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _prepare_postgres_url(url: str) -> tuple[str, dict[str, Any]]:
    """Strip sslmode from URL (breaks asyncpg) and set SSL for cloud Postgres."""
    if "postgres" not in url:
        return url, {}

    parsed = urlparse(url)
    blocked = {"sslmode", "sslcert", "sslkey", "sslrootcert"}
    params = [(key, value) for key, value in parse_qsl(parsed.query) if key not in blocked]
    clean_url = urlunparse(parsed._replace(query=urlencode(params)))

    host = (parsed.hostname or "").lower()
    if host.endswith("railway.internal") or host in {"localhost", "127.0.0.1"}:
        return clean_url, {}

    return clean_url, {"ssl": True}


def get_engine() -> AsyncEngine:
    """Create or return the async database engine."""
    global _engine
    try:
        if _engine is None:
            settings = get_settings()
            database_url = settings.database_url
            engine_kwargs: dict[str, Any] = {
                "echo": settings.debug,
            }
            if settings.standalone_mode:
                engine_kwargs["connect_args"] = {"check_same_thread": False}
            else:
                database_url, pg_connect_args = _prepare_postgres_url(database_url)
                engine_kwargs["connect_args"] = pg_connect_args
                engine_kwargs.update(pool_pre_ping=True, pool_size=10, max_overflow=20)
            _engine = create_async_engine(database_url, **engine_kwargs)
        return _engine
    except Exception as exc:
        logger.error("database_engine_init_failed", error=str(exc))
        raise RuntimeError(f"Failed to initialize database engine: {exc}") from exc


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create or return the async session factory."""
    global _session_factory
    try:
        if _session_factory is None:
            _session_factory = async_sessionmaker(
                bind=get_engine(),
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )
        return _session_factory
    except Exception as exc:
        logger.error("session_factory_init_failed", error=str(exc))
        raise RuntimeError(f"Failed to initialize session factory: {exc}") from exc


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session."""
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception as exc:
        await session.rollback()
        logger.error("db_session_error", error=str(exc))
        raise
    finally:
        await session.close()


async def init_db() -> None:
    """Create all database tables."""
    try:
        settings = get_settings()
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info(
            "database_initialized",
            standalone=settings.standalone_mode,
            host=urlparse(settings.database_url).hostname,
        )
    except Exception as exc:
        logger.error("database_init_failed", error=str(exc))
        raise RuntimeError(
            "Failed to initialize database. On Railway, paste DATABASE_URL from the "
            "Postgres service (or set DATABASE_PRIVATE_URL). "
            f"Details: {exc}"
        ) from exc


async def close_db() -> None:
    """Dispose of the database engine."""
    global _engine, _session_factory
    try:
        if _engine is not None:
            await _engine.dispose()
            _engine = None
            _session_factory = None
            logger.info("database_closed")
    except Exception as exc:
        logger.error("database_close_failed", error=str(exc))
        raise RuntimeError(f"Failed to close database: {exc}") from exc


async def health_check_db() -> dict[str, Any]:
    """Check database connectivity."""
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as exc:
        logger.error("database_health_check_failed", error=str(exc))
        return {"status": "unhealthy", "database": str(exc)}
