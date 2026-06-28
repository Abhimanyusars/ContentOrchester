"""ARQ worker for processing content jobs in the background."""

from __future__ import annotations

import uuid

import structlog
from arq.connections import RedisSettings

from app.database import get_session_factory
from app.redis_settings import build_arq_redis_settings
from app.services.brief_service import BriefService
from app.services.content_service import ContentService

logger = structlog.get_logger(__name__)


async def process_brief_phase1(ctx: dict, job_id: str) -> dict[str, str]:
    """ARQ task: run phase 1 of the brief pipeline."""
    try:
        logger.info("worker_phase1", job_id=job_id)
        session_factory = get_session_factory()
        async with session_factory() as session:
            service = BriefService(session)
            job = await service.run_phase1(uuid.UUID(job_id))
            await session.commit()
            return {"job_id": job_id, "status": job.status.value}
    except Exception as exc:
        logger.error("worker_phase1_failed", job_id=job_id, error=str(exc))
        raise RuntimeError(f"Phase 1 worker failed: {exc}") from exc


async def process_content_job(ctx: dict, job_id: str) -> dict[str, str]:
    """ARQ task: run the multi-agent pipeline for a content job."""
    try:
        logger.info("worker_processing_job", job_id=job_id)
        session_factory = get_session_factory()
        async with session_factory() as session:
            service = ContentService(session)
            job = await service.run_pipeline(uuid.UUID(job_id))
            await session.commit()
            return {
                "job_id": job_id,
                "status": job.status.value,
            }
    except Exception as exc:
        logger.error("worker_job_failed", job_id=job_id, error=str(exc))
        raise RuntimeError(f"Worker failed to process job {job_id}: {exc}") from exc


async def startup(ctx: dict) -> None:
    """ARQ worker startup hook."""
    try:
        logger.info("worker_started")
    except Exception as exc:
        logger.error("worker_startup_failed", error=str(exc))
        raise


async def shutdown(ctx: dict) -> None:
    """ARQ worker shutdown hook."""
    try:
        from app.database import close_db
        await close_db()
        logger.info("worker_shutdown_complete")
    except Exception as exc:
        logger.error("worker_shutdown_failed", error=str(exc))


def _build_redis_settings() -> RedisSettings:
    """Build Redis settings from app config."""
    try:
        return build_arq_redis_settings()
    except Exception as exc:
        raise RuntimeError(f"Failed to build worker Redis settings: {exc}") from exc


class WorkerSettings:
    """ARQ worker configuration."""

    redis_settings = _build_redis_settings()
    functions = [process_content_job, process_brief_phase1]
    on_startup = startup
    on_shutdown = shutdown
    job_timeout = 600
