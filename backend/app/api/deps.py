"""FastAPI dependency injection helpers."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.services.content_service import ContentService
from app.services.brief_service import BriefService


async def get_content_service() -> AsyncGenerator[ContentService, None]:
    """Yield a ContentService bound to the current DB session."""
    async for session in get_db_session():
        try:
            yield ContentService(session)
        except Exception as exc:
            raise RuntimeError(f"Failed to create content service: {exc}") from exc


async def get_brief_service() -> AsyncGenerator[BriefService, None]:
    """Yield a BriefService bound to the current DB session."""
    async for session in get_db_session():
        try:
            yield BriefService(session)
        except Exception as exc:
            raise RuntimeError(f"Failed to create brief service: {exc}") from exc
