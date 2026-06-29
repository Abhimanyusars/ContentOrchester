"""Brief service — pipeline orchestration with human review."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import NODE_STATUS_MAP, run_phase1_pipeline, run_phase2_pipeline
from app.agents.state import ContentAgentState
from app.models.content import ContentJob, ContentStatus
from app.schemas.brief import ApproveRequest, ContentBrief
from app.services.pipeline_broadcaster import broadcaster

logger = structlog.get_logger(__name__)

TOKEN_COST_PER_1K = 0.0001  # estimated per-token cost for analytics


class BriefService:
    """Business logic for briefs API."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _broadcast(self, job: ContentJob, message: str | None = None) -> None:
        """Send WebSocket status update."""
        try:
            await broadcaster.broadcast(
                str(job.id),
                {
                    "task_id": str(job.id),
                    "status": job.status.value,
                    "current_node": job.current_node,
                    "message": message,
                },
            )
        except Exception as exc:
            logger.error("broadcast_failed", job_id=str(job.id), error=str(exc))

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimate from character count."""
        try:
            return max(1, len(text) // 4)
        except Exception:
            return 0

    async def create_brief(self, brief: ContentBrief, client_id: str) -> ContentJob:
        """Create a content job from a brief."""
        try:
            job = ContentJob(
                client_id=client_id,
                topic=brief.topic,
                content_type=brief.content_type,
                tone=brief.brand_voice,
                brand_voice=brief.brand_voice,
                target_audience=brief.target_audience,
                keywords=brief.keywords,
                target_length=brief.target_length,
                status=ContentStatus.PENDING,
                current_node=None,
                agent_logs=[],
            )
            self._session.add(job)
            await self._session.flush()
            await self._session.refresh(job)
            logger.info("brief_created", task_id=str(job.id), client_id=client_id)
            return job
        except Exception as exc:
            logger.error("brief_create_failed", error=str(exc))
            raise RuntimeError(f"Failed to create brief: {exc}") from exc

    async def get_job(self, job_id: uuid.UUID) -> ContentJob | None:
        """Fetch job by ID."""
        try:
            result = await self._session.execute(
                select(ContentJob).where(ContentJob.id == job_id)
            )
            return result.scalar_one_or_none()
        except Exception as exc:
            logger.error("brief_get_failed", job_id=str(job_id), error=str(exc))
            raise RuntimeError(f"Failed to get brief: {exc}") from exc

    async def _set_status(
        self,
        job: ContentJob,
        status: ContentStatus,
        current_node: str | None = None,
        message: str | None = None,
    ) -> None:
        """Update job status and broadcast."""
        try:
            job.status = status
            job.current_node = current_node
            job.updated_at = datetime.now(timezone.utc)
            await self._session.flush()
            await self._session.commit()
            await self._broadcast(job, message)
        except Exception as exc:
            logger.error("status_update_failed", error=str(exc))
            raise RuntimeError(f"Failed to update status: {exc}") from exc

    async def run_phase1(self, job_id: uuid.UUID) -> ContentJob:
        """Execute phase 1: research → write → seo → human review."""
        try:
            job = await self.get_job(job_id)
            if job is None:
                raise ValueError(f"Job {job_id} not found")

            await self._set_status(job, ContentStatus.RESEARCHING, "researcher", "Researching topic")

            result = await run_phase1_pipeline(
                job_id=str(job_id),
                topic=job.topic,
                content_type=job.content_type,
                tone=job.tone,
                brand_voice=job.brand_voice,
                target_audience=job.target_audience or "general audience",
                keywords=job.keywords or [],
                target_length=job.target_length,
                revision_feedback=job.revision_feedback or "",
                research_notes=job.research_notes or "",
                draft_content=job.draft_content or "",
            )

            await self._apply_pipeline_result(job, result)

            if result.get("error"):
                job.status = ContentStatus.FAILED
                job.error_message = result["error"]
            else:
                job.status = ContentStatus.HUMAN_REVIEW
                job.current_node = "human_review"
                job.error_message = None

            job.updated_at = datetime.now(timezone.utc)
            await self._session.flush()
            await self._session.commit()
            await self._broadcast(job, "Awaiting human review")
            return job
        except Exception as exc:
            logger.error("phase1_run_failed", job_id=str(job_id), error=str(exc))
            job = await self.get_job(job_id)
            if job:
                job.status = ContentStatus.FAILED
                job.error_message = str(exc)
                await self._session.commit()
            raise RuntimeError(f"Phase 1 failed: {exc}") from exc

    async def _apply_pipeline_result(self, job: ContentJob, result: dict[str, Any]) -> None:
        """Persist pipeline output to the job."""
        try:
            job.research_notes = result.get("research_notes") or job.research_notes
            job.draft_content = result.get("draft_content") or job.draft_content
            job.final_content = result.get("final_content") or job.final_content
            existing_logs = job.agent_logs or []
            job.agent_logs = existing_logs + result.get("agent_logs", [])
            text = (job.draft_content or "") + (job.final_content or "") + (job.research_notes or "")
            job.tokens_used += self._estimate_tokens(text)
        except Exception as exc:
            logger.error("apply_result_failed", error=str(exc))
            raise RuntimeError(f"Failed to apply pipeline result: {exc}") from exc

    async def approve_content(
        self,
        content_id: uuid.UUID,
        request: ApproveRequest,
        client_id: str,
    ) -> ContentJob:
        """Handle human review approval or revision request."""
        try:
            job = await self.get_job(content_id)
            if job is None:
                raise ValueError(f"Content {content_id} not found")
            if job.client_id != client_id:
                raise PermissionError("Not authorized for this content")

            job.approved = request.approved

            if request.approved:
                await self._set_status(job, ContentStatus.QUALITY_CHECK, "editor", "Quality check")
                state: ContentAgentState = {
                    "job_id": str(job.id),
                    "topic": job.topic,
                    "content_type": job.content_type,
                    "tone": job.tone,
                    "brand_voice": job.brand_voice,
                    "target_audience": job.target_audience or "",
                    "keywords": job.keywords or [],
                    "target_length": job.target_length,
                    "revision_feedback": "",
                    "research_notes": job.research_notes or "",
                    "draft_content": job.draft_content or "",
                    "final_content": "",
                    "current_agent": "",
                    "agent_logs": [],
                    "error": "",
                    "messages": [],
                }
                result = await run_phase2_pipeline(state)
                await self._apply_pipeline_result(job, result)

                if result.get("error"):
                    job.status = ContentStatus.FAILED
                    job.error_message = result["error"]
                else:
                    job.status = ContentStatus.COMPLETED
                    job.current_node = "publish"
                    job.quality_score = 85.0
                    job.error_message = None

                job.updated_at = datetime.now(timezone.utc)
                await self._session.commit()
                await self._broadcast(job, "Content published")
                return job

            # Revision requested
            job.revision_feedback = request.feedback or "Please revise the content."
            job.status = ContentStatus.REVISION
            job.current_node = "writer"
            await self._session.commit()
            return await self.run_phase1(job.id)

        except PermissionError:
            raise
        except Exception as exc:
            logger.error("approve_failed", content_id=str(content_id), error=str(exc))
            raise RuntimeError(f"Approval failed: {exc}") from exc

    async def get_analytics(self, client_id: str) -> dict[str, Any]:
        """Return analytics for a client."""
        try:
            result = await self._session.execute(
                select(
                    func.count(ContentJob.id),
                    func.avg(ContentJob.quality_score),
                    func.sum(ContentJob.tokens_used),
                ).where(ContentJob.client_id == client_id)
            )
            row = result.one()
            total = row[0] or 0
            avg_score = float(row[1] or 0.0)
            total_tokens = int(row[2] or 0)
            return {
                "client_id": client_id,
                "total_pieces": total,
                "avg_quality_score": round(avg_score, 2),
                "total_tokens_used": total_tokens,
                "estimated_cost_usd": round((total_tokens / 1000) * TOKEN_COST_PER_1K, 4),
            }
        except Exception as exc:
            logger.error("analytics_failed", client_id=client_id, error=str(exc))
            raise RuntimeError(f"Analytics failed: {exc}") from exc
