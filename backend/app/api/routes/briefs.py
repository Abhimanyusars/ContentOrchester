"""Brief API routes (prompt 4)."""

from __future__ import annotations

import uuid

import structlog
from arq import create_pool
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.api.auth import create_access_token, get_current_client
from app.api.deps import get_brief_service
from app.config import get_settings
from app.database import get_session_factory
from app.models.content import ContentStatus
from app.redis_settings import build_arq_redis_settings
from app.schemas.brief import (
    ApproveRequest,
    ApproveResponse,
    BriefCreateResponse,
    BriefStatusResponse,
    ClientAnalyticsResponse,
    ContentBrief,
    ContentResponse,
    TokenRequest,
    TokenResponse,
)
from app.services.brief_service import BriefService

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["briefs"])


async def _enqueue_phase1(job_id: uuid.UUID) -> None:
    """Enqueue phase 1 via ARQ."""
    try:
        pool = await create_pool(build_arq_redis_settings())
        await pool.enqueue_job("process_brief_phase1", str(job_id))
        await pool.close()
    except Exception as exc:
        logger.error("enqueue_failed", job_id=str(job_id), error=str(exc))
        raise RuntimeError(f"Failed to enqueue job: {exc}") from exc


async def _run_phase1_background(job_id: uuid.UUID) -> None:
    """Run phase 1 in-process (standalone mode)."""
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            service = BriefService(session)
            await service.run_phase1(job_id)
            await session.commit()
    except Exception as exc:
        logger.error("background_phase1_failed", job_id=str(job_id), error=str(exc))


@router.post("/auth/token", response_model=TokenResponse)
async def issue_token(data: TokenRequest) -> TokenResponse:
    """Issue a JWT for API access (dev / client onboarding)."""
    try:
        token = create_access_token(data.client_id)
        return TokenResponse(access_token=token, client_id=data.client_id)
    except Exception as exc:
        logger.error("token_issue_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/briefs", response_model=BriefCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_brief(
    brief: ContentBrief,
    background_tasks: BackgroundTasks,
    client_id: str = Depends(get_current_client),
    service: BriefService = Depends(get_brief_service),
) -> BriefCreateResponse:
    """Accept a ContentBrief, start the pipeline, return task_id."""
    try:
        job = await service.create_brief(brief, client_id)
        settings = get_settings()
        if settings.standalone_mode:
            background_tasks.add_task(_run_phase1_background, job.id)
        else:
            await _enqueue_phase1(job.id)
        return BriefCreateResponse(task_id=job.id, status=job.status.value)
    except Exception as exc:
        logger.error("create_brief_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/briefs/{task_id}/status", response_model=BriefStatusResponse)
async def get_brief_status(
    task_id: uuid.UUID,
    client_id: str = Depends(get_current_client),
    service: BriefService = Depends(get_brief_service),
) -> BriefStatusResponse:
    """Return pipeline status and current node."""
    try:
        job = await service.get_job(task_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Task not found")
        if job.client_id != client_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        return BriefStatusResponse(
            task_id=job.id,
            status=job.status.value,
            current_node=job.current_node,
            error_message=job.error_message,
            updated_at=job.updated_at,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_status_failed", task_id=str(task_id), error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/content/{content_id}", response_model=ContentResponse)
async def get_content(
    content_id: uuid.UUID,
    client_id: str = Depends(get_current_client),
    service: BriefService = Depends(get_brief_service),
) -> ContentResponse:
    """Return draft or final content."""
    try:
        job = await service.get_job(content_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Content not found")
        if job.client_id != client_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        return ContentResponse(
            content_id=job.id,
            status=job.status.value,
            title=job.topic,
            draft_content=job.draft_content,
            final_content=job.final_content,
            research_notes=job.research_notes,
            quality_score=job.quality_score,
            agent_logs=job.agent_logs,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_content_failed", content_id=str(content_id), error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/content/{content_id}/approve", response_model=ApproveResponse)
async def approve_content(
    content_id: uuid.UUID,
    request: ApproveRequest,
    background_tasks: BackgroundTasks,
    client_id: str = Depends(get_current_client),
    service: BriefService = Depends(get_brief_service),
) -> ApproveResponse:
    """Resume pipeline after human review."""
    try:
        job = await service.get_job(content_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Content not found")
        if job.status != ContentStatus.HUMAN_REVIEW:
            raise HTTPException(status_code=400, detail="Content is not awaiting review")

        if request.approved:
            settings = get_settings()
            if settings.standalone_mode:
                background_tasks.add_task(_approve_background, content_id, request, client_id)
                return ApproveResponse(
                    content_id=content_id,
                    status="quality_check",
                    message="Approval received — finishing pipeline",
                )
            job = await service.approve_content(content_id, request, client_id)
        else:
            if not request.feedback:
                raise HTTPException(status_code=400, detail="Feedback required for revision")
            settings = get_settings()
            if settings.standalone_mode:
                background_tasks.add_task(_approve_background, content_id, request, client_id)
                return ApproveResponse(
                    content_id=content_id,
                    status="revision",
                    message="Revision requested — re-running pipeline",
                )
            job = await service.approve_content(content_id, request, client_id)

        return ApproveResponse(
            content_id=job.id,
            status=job.status.value,
            message="Pipeline updated",
        )
    except HTTPException:
        raise
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("approve_endpoint_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc


async def _approve_background(
    content_id: uuid.UUID,
    request: ApproveRequest,
    client_id: str,
) -> None:
    """Background approval handler."""
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            service = BriefService(session)
            await service.approve_content(content_id, request, client_id)
            await session.commit()
    except Exception as exc:
        logger.error("background_approve_failed", content_id=str(content_id), error=str(exc))


@router.get("/clients/{client_id}/analytics", response_model=ClientAnalyticsResponse)
async def get_client_analytics(
    client_id: str,
    current_client: str = Depends(get_current_client),
    service: BriefService = Depends(get_brief_service),
) -> ClientAnalyticsResponse:
    """Return analytics for a client."""
    try:
        if current_client != client_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        data = await service.get_analytics(client_id)
        return ClientAnalyticsResponse(**data)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("analytics_endpoint_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc
