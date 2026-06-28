"""Content job ORM model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, Enum, Float, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ContentStatus(str, enum.Enum):
    """Lifecycle status of a content creation job."""

    PENDING = "pending"
    RESEARCHING = "researching"
    WRITING = "writing"
    SEO = "seo"
    HUMAN_REVIEW = "human_review"
    QUALITY_CHECK = "quality_check"
    PUBLISHING = "publishing"
    EDITING = "editing"
    COMPLETED = "completed"
    FAILED = "failed"
    REVISION = "revision"


class ContentJob(Base):
    """A multi-agent content creation job."""

    __tablename__ = "content_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    client_id: Mapped[str] = mapped_column(String(100), default="default", nullable=False)
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), default="blog_post")
    tone: Mapped[str] = mapped_column(String(100), default="professional")
    brand_voice: Mapped[str] = mapped_column(String(100), default="professional")
    target_audience: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    keywords: Mapped[Optional[list[str]]] = mapped_column(JSON, default=list)
    target_length: Mapped[int] = mapped_column(Integer, default=800)
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=ContentStatus.PENDING,
        nullable=False,
    )
    current_node: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    research_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    draft_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    final_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    revision_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved: Mapped[Optional[bool]] = mapped_column(nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    agent_logs: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON, default=list)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
