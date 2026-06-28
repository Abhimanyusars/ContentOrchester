"""Content job business logic."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import run_content_pipeline
from app.models.content import ContentJob, ContentStatus
from app.schemas.content import ContentJobCreate

logger = structlog.get_logger(__name__)


class ContentService:
    """Service layer for content job CRUD and pipeline execution."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_job(self, data: ContentJobCreate) -> ContentJob:
        """Create a new pending content job."""
        try:
            job = ContentJob(
                topic=data.topic,
                content_type=data.content_type,
                tone=data.tone,
                brand_voice=data.tone,
                target_audience=data.target_audience,
                keywords=[],
                target_length=800,
                status=ContentStatus.PENDING,
                agent_logs=[],
            )
            self._session.add(job)
            await self._session.flush()
            await self._session.refresh(job)
            logger.info("job_created", job_id=str(job.id), topic=data.topic)
            return job
        except Exception as exc:
            logger.error("job_create_failed", error=str(exc))
            raise RuntimeError(f"Failed to create content job: {exc}") from exc

    async def get_job(self, job_id: uuid.UUID) -> ContentJob | None:
        """Fetch a content job by ID."""
        try:
            result = await self._session.execute(
                select(ContentJob).where(ContentJob.id == job_id)
            )
            return result.scalar_one_or_none()
        except Exception as exc:
            logger.error("job_get_failed", job_id=str(job_id), error=str(exc))
            raise RuntimeError(f"Failed to get content job: {exc}") from exc

    async def list_jobs(self, limit: int = 50, offset: int = 0) -> list[ContentJob]:
        """List content jobs ordered by creation date."""
        try:
            result = await self._session.execute(
                select(ContentJob)
                .order_by(ContentJob.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars().all())
        except Exception as exc:
            logger.error("job_list_failed", error=str(exc))
            raise RuntimeError(f"Failed to list content jobs: {exc}") from exc

    async def _update_status(self, job: ContentJob, status: ContentStatus) -> None:
        """Update job status and timestamp."""
        try:
            job.status = status
            job.updated_at = datetime.now(timezone.utc)
            await self._session.flush()
            await self._session.commit()
        except Exception as exc:
            logger.error("status_update_failed", job_id=str(job.id), error=str(exc))
            raise RuntimeError(f"Failed to update job status: {exc}") from exc

    async def run_pipeline(self, job_id: uuid.UUID) -> ContentJob:
        """Execute the multi-agent pipeline for a job."""
        try:
            job = await self.get_job(job_id)
            if job is None:
                raise ValueError(f"Job {job_id} not found")

            await self._update_status(job, ContentStatus.RESEARCHING)

            result = await run_content_pipeline(
                job_id=str(job_id),
                topic=job.topic,
                content_type=job.content_type,
                tone=job.tone,
                target_audience=job.target_audience or "general audience",
            )

            if result.get("error"):
                job.status = ContentStatus.FAILED
                job.error_message = result["error"]
            else:
                job.research_notes = result.get("research_notes")
                job.draft_content = result.get("draft_content")
                job.final_content = result.get("final_content")
                job.status = ContentStatus.COMPLETED
                job.error_message = None

            job.agent_logs = result.get("agent_logs", [])
            job.updated_at = datetime.now(timezone.utc)
            await self._session.flush()
            await self._session.refresh(job)

            logger.info("pipeline_finished", job_id=str(job_id), status=job.status.value)
            return job
        except Exception as exc:
            logger.error("pipeline_run_failed", job_id=str(job_id), error=str(exc))
            try:
                job = await self.get_job(job_id)
                if job:
                    job.status = ContentStatus.FAILED
                    job.error_message = str(exc)
                    job.updated_at = datetime.now(timezone.utc)
                    await self._session.flush()
            except Exception:
                pass
            raise RuntimeError(f"Pipeline execution failed: {exc}") from exc

    async def delete_job(self, job_id: uuid.UUID) -> bool:
        """Delete a content job."""
        try:
            job = await self.get_job(job_id)
            if job is None:
                return False
            await self._session.delete(job)
            await self._session.flush()
            logger.info("job_deleted", job_id=str(job_id))
            return True
        except Exception as exc:
            logger.error("job_delete_failed", job_id=str(job_id), error=str(exc))
            raise RuntimeError(f"Failed to delete content job: {exc}") from exc
