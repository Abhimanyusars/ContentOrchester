"""Writer agent — creates draft content from research notes."""

from __future__ import annotations

import structlog

from app.agents.state import AgentLog, ContentAgentState
from app.services.llm_client import get_llm_client

logger = structlog.get_logger(__name__)

WRITER_SYSTEM = """You are a skilled content writer. You create engaging, well-structured
content based on research notes provided to you.

Guidelines:
- Match the requested tone and content type
- Write for the specified target audience
- Use clear headings and logical flow
- Include compelling introductions and conclusions
- Back claims with facts from the research notes
- Aim for 800-1200 words unless otherwise specified"""


async def writer_node(state: ContentAgentState) -> dict:
    """Write draft content based on research notes."""
    try:
        if state.get("error"):
            return {"current_agent": "writer", "error": state["error"]}

        topic = state["topic"]
        research_notes = state.get("research_notes", "")
        content_type = state["content_type"]
        tone = state.get("brand_voice") or state["tone"]
        target_audience = state.get("target_audience", "general audience")
        target_length = state.get("target_length", 800)
        keywords = state.get("keywords", [])
        revision_feedback = state.get("revision_feedback", "")

        if not research_notes and not revision_feedback:
            raise ValueError("No research notes available for writing")

        logger.info("writer_started", topic=topic)

        llm = get_llm_client()
        keyword_str = ", ".join(keywords) if keywords else "none"
        feedback_block = f"\nRevision feedback to address:\n{revision_feedback}\n" if revision_feedback else ""
        user_prompt = f"""Write a {content_type} about: {topic}

Brand voice / tone: {tone}
Target Audience: {target_audience}
Target length: ~{target_length} words
Keywords to include: {keyword_str}
{feedback_block}
Research Notes:
{research_notes or "Use revision feedback and topic only."}

Create a complete draft."""

        draft_content = await llm.generate(
            system_prompt=WRITER_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.7,
        )

        log_entry: AgentLog = {
            "agent": "writer",
            "action": "completed_draft",
            "summary": f"Drafted {content_type} — {len(draft_content)} chars",
        }

        logger.info("writer_completed", topic=topic)
        return {
            "draft_content": draft_content,
            "current_agent": "writer",
            "agent_logs": [log_entry],
            "error": "",
        }
    except Exception as exc:
        logger.error("writer_failed", error=str(exc))
        return {
            "current_agent": "writer",
            "error": f"Writer failed: {exc}",
            "agent_logs": [{
                "agent": "writer",
                "action": "failed",
                "summary": str(exc),
            }],
        }
