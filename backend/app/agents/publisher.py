"""Publisher agent — finalizes approved content for delivery."""

from __future__ import annotations

import structlog

from app.agents.state import AgentLog, ContentAgentState

logger = structlog.get_logger(__name__)


async def publisher_node(state: ContentAgentState) -> dict:
    """Mark content as published and set final output."""
    try:
        if state.get("error"):
            return {"current_agent": "publish", "error": state["error"]}

        content = state.get("final_content") or state.get("draft_content", "")
        if not content:
            raise ValueError("No content to publish")

        logger.info("publisher_started", job_id=state["job_id"])
        log_entry: AgentLog = {
            "agent": "publish",
            "action": "published",
            "summary": f"Published — {len(content)} chars",
        }
        return {
            "final_content": content,
            "current_agent": "publish",
            "agent_logs": [log_entry],
            "error": "",
        }
    except Exception as exc:
        logger.error("publisher_failed", error=str(exc))
        return {
            "current_agent": "publish",
            "error": f"Publish failed: {exc}",
            "agent_logs": [{"agent": "publish", "action": "failed", "summary": str(exc)}],
        }
