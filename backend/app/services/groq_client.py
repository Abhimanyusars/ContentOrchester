"""Async Groq LLM client — OpenAI-compatible API for cloud deployment."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)


class GroqClient:
    """Async client for Groq's OpenAI-compatible chat API."""

    def __init__(self) -> None:
        try:
            settings = get_settings()
            self._base_url = settings.groq_base_url.rstrip("/")
            self._model = settings.groq_model
            self._api_key = settings.groq_api_key
            self._timeout = settings.ollama_timeout_seconds
            if not self._api_key:
                raise ValueError("GROQ_API_KEY is required when LLM_PROVIDER=groq")
        except Exception as exc:
            logger.error("groq_client_init_failed", error=str(exc))
            raise RuntimeError(f"Failed to initialize Groq client: {exc}") from exc

    async def _chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
    ) -> str:
        """Send a chat request to Groq."""
        try:
            payload: dict[str, Any] = {
                "model": self._model,
                "messages": messages,
                "temperature": temperature,
            }
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            }
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()

            choices = data.get("choices", [])
            if not choices:
                raise ValueError("No choices in Groq response")
            content = choices[0].get("message", {}).get("content", "")
            if not content:
                raise ValueError("No text content in Groq response")
            return content
        except httpx.HTTPStatusError as exc:
            logger.error("groq_http_error", status=exc.response.status_code, error=str(exc))
            raise RuntimeError(f"Groq HTTP error: {exc}") from exc
        except Exception as exc:
            logger.error("groq_chat_failed", error=str(exc))
            raise RuntimeError(f"Groq chat failed: {exc}") from exc

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
    ) -> str:
        """Generate text using Groq."""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            return await self._chat(messages, temperature=temperature)
        except Exception as exc:
            logger.error("groq_generate_failed", error=str(exc))
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
            logger.error("groq_generate_context_failed", error=str(exc))
            raise RuntimeError(f"Failed to generate with context: {exc}") from exc

    async def health_check(self) -> bool:
        """Check if Groq API is reachable."""
        try:
            headers = {"Authorization": f"Bearer {self._api_key}"}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self._base_url}/models", headers=headers)
                return response.status_code == 200
        except Exception as exc:
            logger.error("groq_health_check_failed", error=str(exc))
            return False
