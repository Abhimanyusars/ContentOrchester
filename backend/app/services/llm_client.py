"""Async Groq LLM client factory."""

from __future__ import annotations

import structlog

from app.config import get_settings
from app.services.groq_client import GroqClient

logger = structlog.get_logger(__name__)

LLMClient = GroqClient
_client_instance: GroqClient | None = None
_client_key: str | None = None


def get_llm_client() -> GroqClient:
    """Return singleton Groq LLM client."""
    global _client_instance, _client_key
    try:
        settings = get_settings()
        key = f"{settings.groq_model}:{settings.groq_base_url}"
        if _client_instance is None or _client_key != key:
            _client_instance = GroqClient()
            _client_key = key
        return _client_instance
    except Exception as exc:
        raise RuntimeError(f"Failed to get LLM client: {exc}") from exc
