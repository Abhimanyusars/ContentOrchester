"""Content job API endpoints."""

from __future__ import annotations

import uuid

import structlog
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status

from app.api.deps import get_content_service
from app.config import get_settings
from app.database import get_session_factory
from app.schemas.content import ContentJobCreate, ContentJobResponse, ContentJobStatus
from app.services.content_service import ContentService

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/content", tags=["content"])


async def _run_job_standalone(job_id: uuid.UUID) -> None:
    """Run pipeline in-process (standalone mode, no Redis worker)."""
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            service = ContentService(session)
            await service.run_pipeline(job_id)
            await session.commit()
        logger.info("standalone_job_completed", job_id=str(job_id))
    except Exception as exc:
        logger.error("standalone_job_failed", job_id=str(job_id), error=str(exc))


async def _enqueue_job(job_id: uuid.UUID) -> None:
    """Enqueue a content job for background processing via ARQ."""
    try:
        settings = get_settings()
        redis_settings = RedisSettings(
            host=settings.redis_host,
            port=settings.redis_port,
            database=settings.redis_db,
            password=settings.redis_password,
        )
        pool = await create_pool(redis_settings)
        await pool.enqueue_job("process_content_job", str(job_id))
        await pool.close()
        logger.info("job_enqueued", job_id=str(job_id))
    except Exception as exc:
        logger.error("job_enqueue_failed", job_id=str(job_id), error=str(exc))
        raise RuntimeError(f"Failed to enqueue job: {exc}") from exc


@router.post("", response_model=ContentJobResponse, status_code=status.HTTP_201_CREATED)
async def create_content_job(
    data: ContentJobCreate,
    background_tasks: BackgroundTasks,
    service: ContentService = Depends(get_content_service),
) -> ContentJobResponse:
    """Create a new content job and enqueue it for processing."""
    try:
        job = await service.create_job(data)
        settings = get_settings()
        if settings.standalone_mode:
            background_tasks.add_task(_run_job_standalone, job.id)
        else:
            await _enqueue_job(job.id)
        return ContentJobResponse.model_validate(job)
    except Exception as exc:
        logger.error("create_content_job_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("", response_model=list[ContentJobResponse])
async def list_content_jobs(
    limit: int = 50,
    offset: int = 0,
    service: ContentService = Depends(get_content_service),
) -> list[ContentJobResponse]:
    """List all content jobs."""
    try:
        jobs = await service.list_jobs(limit=limit, offset=offset)
        return [ContentJobResponse.model_validate(job) for job in jobs]
    except Exception as exc:
        logger.error("list_content_jobs_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("/{job_id}", response_model=ContentJobResponse)
async def get_content_job(
    job_id: uuid.UUID,
    service: ContentService = Depends(get_content_service),
) -> ContentJobResponse:
    """Get a single content job by ID."""
    try:
        job = await service.get_job(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            )
        return ContentJobResponse.model_validate(job)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_content_job_failed", job_id=str(job_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("/{job_id}/status", response_model=ContentJobStatus)
async def get_content_job_status(
    job_id: uuid.UUID,
    service: ContentService = Depends(get_content_service),
) -> ContentJobStatus:
    """Get lightweight status for polling."""
    try:
        job = await service.get_job(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            )
        return ContentJobStatus(
            id=job.id,
            status=job.status.value,
            error_message=job.error_message,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_job_status_failed", job_id=str(job_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_content_job(
    job_id: uuid.UUID,
    service: ContentService = Depends(get_content_service),
) -> Response:
    """Delete a content job."""
    try:
        deleted = await service.delete_job(job_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("delete_content_job_failed", job_id=str(job_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
