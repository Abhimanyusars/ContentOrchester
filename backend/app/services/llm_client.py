"""Async Ollama LLM client — free, runs locally, no API key required."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)


class OllamaClient:
    """Async client for Ollama's local chat API."""

    def __init__(self) -> None:
        try:
            settings = get_settings()
            self._base_url = settings.ollama_base_url.rstrip("/")
            self._model = settings.ollama_model
            self._timeout = settings.ollama_timeout_seconds
        except Exception as exc:
            logger.error("ollama_client_init_failed", error=str(exc))
            raise RuntimeError(f"Failed to initialize Ollama client: {exc}") from exc

    async def _chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
    ) -> str:
        """Send a chat request to Ollama."""
        try:
            payload: dict[str, Any] = {
                "model": self._model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
            }
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

            content = data.get("message", {}).get("content", "")
            if not content:
                raise ValueError("No text content in Ollama response")
            return content
        except httpx.HTTPStatusError as exc:
            logger.error("ollama_http_error", status=exc.response.status_code, error=str(exc))
            raise RuntimeError(f"Ollama HTTP error: {exc}") from exc
        except Exception as exc:
            logger.error("ollama_chat_failed", error=str(exc))
            raise RuntimeError(f"Ollama chat failed: {exc}") from exc

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
    ) -> str:
        """Generate text using Ollama."""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            return await self._chat(messages, temperature=temperature)
        except Exception as exc:
            logger.error("ollama_generate_failed", error=str(exc))
            raise RuntimeError(f"Failed to generate content: {exc}") from exc

    async def generate_with_context(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
    ) -> str:
        """Generate text with multi-turn message history."""
        try:
            full_messages = [{"role": "system", "content": system_prompt}, *messages]
            return await self._chat(full_messages, temperature=temperature)
        except Exception as exc:
            logger.error("ollama_generate_context_failed", error=str(exc))
            raise RuntimeError(f"Failed to generate with context: {exc}") from exc

    async def health_check(self) -> bool:
        """Check if Ollama is reachable."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                return response.status_code == 200
        except Exception as exc:
            logger.error("ollama_health_check_failed", error=str(exc))
            return False


_client_instance: OllamaClient | None = None


def get_llm_client() -> OllamaClient:
    """Return singleton Ollama client."""
    global _client_instance
    try:
        settings = get_settings()
        if _client_instance is None or _client_instance._model != settings.ollama_model:
            _client_instance = OllamaClient()
        return _client_instance
    except Exception as exc:
        raise RuntimeError(f"Failed to get LLM client: {exc}") from exc
