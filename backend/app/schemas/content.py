"""Pydantic schemas for content API."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ContentJobCreate(BaseModel):
    """Request body for creating a new content job."""

    topic: str = Field(..., min_length=3, max_length=500, description="Content topic")
    content_type: str = Field(default="blog_post", max_length=100)
    tone: str = Field(default="professional", max_length=100)
    target_audience: str | None = Field(default=None, max_length=255)

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: str) -> str:
        """Ensure topic is not blank."""
        try:
            stripped = value.strip()
            if not stripped:
                raise ValueError("Topic cannot be empty")
            return stripped
        except Exception as exc:
            raise ValueError(f"Invalid topic: {exc}") from exc


class ContentJobResponse(BaseModel):
    """Full content job response."""

    id: UUID
    topic: str
    content_type: str
    tone: str
    target_audience: str | None
    status: str
    research_notes: str | None
    draft_content: str | None
    final_content: str | None
    agent_logs: list[dict[str, str]] | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContentJobStatus(BaseModel):
    """Lightweight status response for polling."""

    id: UUID
    status: str
    error_message: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    services: dict[str, Any]
