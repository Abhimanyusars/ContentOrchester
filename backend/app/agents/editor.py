"""Editor agent — reviews and polishes draft content."""

from __future__ import annotations

import structlog

from app.agents.state import AgentLog, ContentAgentState
from app.services.llm_client import get_llm_client

logger = structlog.get_logger(__name__)

EDITOR_SYSTEM = """You are a meticulous editor. You review and improve content drafts
to make them publication-ready.

Your editing priorities:
1. Clarity and readability
2. Grammar, spelling, and punctuation
3. Logical flow and structure
4. Tone consistency
5. Factual accuracy (flag anything questionable)
6. Engaging headlines and subheadings

Return the fully edited final version. Do not include editor commentary — only the
polished content."""


async def editor_node(state: ContentAgentState) -> dict:
    """Edit and polish the draft content."""
    try:
        if state.get("error"):
            return {"current_agent": "editor", "error": state["error"]}

        draft_content = state.get("draft_content", "")
        topic = state["topic"]
        tone = state["tone"]
        content_type = state["content_type"]

        if not draft_content:
            raise ValueError("No draft content available for editing")

        logger.info("editor_started", topic=topic)

        llm = get_llm_client()
        user_prompt = f"""Edit this {content_type} draft about "{topic}".

Required tone: {tone}

Draft:
{draft_content}

Return the polished, publication-ready final version."""

        final_content = await llm.generate(
            system_prompt=EDITOR_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.4,
        )

        log_entry: AgentLog = {
            "agent": "editor",
            "action": "completed_edit",
            "summary": f"Edited content — {len(final_content)} chars final",
        }

        logger.info("editor_completed", topic=topic)
        return {
            "final_content": final_content,
            "current_agent": "editor",
            "agent_logs": [log_entry],
            "error": "",
        }
    except Exception as exc:
        logger.error("editor_failed", error=str(exc))
        return {
            "current_agent": "editor",
            "error": f"Editor failed: {exc}",
            "agent_logs": [{
                "agent": "editor",
                "action": "failed",
                "summary": str(exc),
            }],
        }
