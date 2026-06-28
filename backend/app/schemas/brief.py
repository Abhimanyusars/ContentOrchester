"""Pydantic schemas for briefs API (prompt 4)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


ContentType = Literal["blog", "linkedin", "email", "blog_post", "linkedin_post", "email_newsletter", "product_description"]
ToneType = Literal["professional", "conversational", "authoritative", "friendly", "casual", "academic", "persuasive", "humorous"]


class ContentBrief(BaseModel):
    """Request body for creating a new content brief."""

    topic: str = Field(..., min_length=3, max_length=500)
    keywords: list[str] = Field(default_factory=list)
    target_audience: str = Field(..., min_length=2, max_length=500)
    brand_voice: ToneType = "professional"
    content_type: ContentType = "blog"
    target_length: int = Field(default=800, ge=300, le=3000)

    @field_validator("topic", "target_audience")
    @classmethod
    def strip_required(cls, value: str) -> str:
        """Strip whitespace from required string fields."""
        try:
            stripped = value.strip()
            if not stripped:
                raise ValueError("Field cannot be empty")
            return stripped
        except Exception as exc:
            raise ValueError(f"Invalid field: {exc}") from exc

    @field_validator("keywords")
    @classmethod
    def normalize_keywords(cls, value: list[str]) -> list[str]:
        """Normalize keyword tags."""
        try:
            return [kw.strip() for kw in value if kw.strip()]
        except Exception as exc:
            raise ValueError(f"Invalid keywords: {exc}") from exc


class BriefCreateResponse(BaseModel):
    """Response after submitting a brief."""

    task_id: UUID
    status: str
    message: str = "Pipeline started"


class BriefStatusResponse(BaseModel):
    """Pipeline status for a brief task."""

    task_id: UUID
    status: str
    current_node: str | None
    error_message: str | None = None
    updated_at: datetime


class ContentResponse(BaseModel):
    """Draft or final content for a job."""

    content_id: UUID
    status: str
    title: str | None = None
    draft_content: str | None = None
    final_content: str | None = None
    research_notes: str | None = None
    quality_score: float | None = None
    agent_logs: list[dict[str, str]] | None = None


class ApproveRequest(BaseModel):
    """Human review approval or revision request."""

    approved: bool
    feedback: str | None = Field(default=None, max_length=2000)


class ApproveResponse(BaseModel):
    """Response after approval action."""

    content_id: UUID
    status: str
    message: str


class ClientAnalyticsResponse(BaseModel):
    """Analytics summary for a client."""

    client_id: str
    total_pieces: int
    avg_quality_score: float
    total_tokens_used: int
    estimated_cost_usd: float


class TokenRequest(BaseModel):
    """Dev token request for JWT auth."""

    client_id: str = Field(..., min_length=1, max_length=100)


class TokenResponse(BaseModel):
    """JWT access token response."""

    access_token: str
    token_type: str = "bearer"
    client_id: str


class WebSocketStatusMessage(BaseModel):
    """WebSocket status update payload."""

    task_id: str
    status: str
    current_node: str | None
    message: str | None = None
