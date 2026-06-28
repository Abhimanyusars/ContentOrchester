"""Tavily web search integration (free tier)."""

from __future__ import annotations

from typing import Any

import structlog
from tavily import AsyncTavilyClient

from app.config import get_settings

logger = structlog.get_logger(__name__)


class TavilySearchService:
    """Async wrapper for Tavily search API."""

    def __init__(self) -> None:
        try:
            settings = get_settings()
            if not settings.tavily_api_key:
                raise ValueError("TAVILY_API_KEY is not configured")
            self._client = AsyncTavilyClient(api_key=settings.tavily_api_key)
            self._max_results = settings.tavily_max_results
        except Exception as exc:
            logger.error("tavily_init_failed", error=str(exc))
            raise RuntimeError(f"Failed to initialize Tavily client: {exc}") from exc

    async def search(self, query: str) -> list[dict[str, Any]]:
        """Perform a web search and return structured results."""
        try:
            response = await self._client.search(
                query=query,
                max_results=self._max_results,
                search_depth="basic",
                include_answer=True,
            )
            results: list[dict[str, Any]] = []
            if response.get("answer"):
                results.append({
                    "title": "AI Summary",
                    "content": response["answer"],
                    "url": "",
                })
            for item in response.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "content": item.get("content", ""),
                    "url": item.get("url", ""),
                })
            return results
        except Exception as exc:
            logger.error("tavily_search_failed", query=query, error=str(exc))
            raise RuntimeError(f"Tavily search failed: {exc}") from exc

    async def search_formatted(self, query: str) -> str:
        """Search and return a formatted text summary for agents."""
        try:
            results = await self.search(query)
            if not results:
                return "No search results found."
            sections: list[str] = []
            for i, result in enumerate(results, start=1):
                section = f"### Source {i}: {result['title']}\n"
                if result.get("url"):
                    section += f"URL: {result['url']}\n"
                section += f"{result['content']}\n"
                sections.append(section)
            return "\n".join(sections)
        except Exception as exc:
            logger.error("tavily_search_formatted_failed", query=query, error=str(exc))
            raise RuntimeError(f"Failed to format search results: {exc}") from exc


_service_instance: TavilySearchService | None = None


def get_tavily_service() -> TavilySearchService:
    """Return singleton Tavily service."""
    global _service_instance
    try:
        if _service_instance is None:
            _service_instance = TavilySearchService()
        return _service_instance
    except Exception as exc:
        raise RuntimeError(f"Failed to get Tavily service: {exc}") from exc
