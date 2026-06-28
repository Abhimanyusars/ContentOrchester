"""SEO agent — optimizes draft content for target keywords."""

from __future__ import annotations

import structlog

from app.agents.state import AgentLog, ContentAgentState
from app.services.llm_client import get_llm_client

logger = structlog.get_logger(__name__)

SEO_SYSTEM = """You are an SEO specialist. Improve the draft content for search visibility
while keeping it natural and readable. Integrate keywords naturally, improve headings,
and suggest a compelling meta description at the top as <!-- meta: ... -->."""


async def seo_node(state: ContentAgentState) -> dict:
    """Apply SEO optimizations to the draft."""
    try:
        if state.get("error"):
            return {"current_agent": "seo", "error": state["error"]}

        draft = state.get("draft_content", "")
        topic = state["topic"]
        keywords = state.get("keywords", [])

        if not draft:
            raise ValueError("No draft available for SEO")

        logger.info("seo_started", topic=topic)
        llm = get_llm_client()
        keyword_str = ", ".join(keywords) if keywords else "none specified"
        user_prompt = f"""Topic: {topic}
Target keywords: {keyword_str}

Draft:
{draft}

Optimize this content for SEO. Return the improved version."""

        optimized = await llm.generate(
            system_prompt=SEO_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.4,
        )

        log_entry: AgentLog = {
            "agent": "seo",
            "action": "completed_seo",
            "summary": f"SEO optimized — {len(optimized)} chars",
        }
        logger.info("seo_completed", topic=topic)
        return {
            "draft_content": optimized,
            "current_agent": "seo",
            "agent_logs": [log_entry],
            "error": "",
        }
    except Exception as exc:
        logger.error("seo_failed", error=str(exc))
        return {
            "current_agent": "seo",
            "error": f"SEO failed: {exc}",
            "agent_logs": [{"agent": "seo", "action": "failed", "summary": str(exc)}],
        }
