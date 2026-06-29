"""Researcher agent — gathers information via Tavily web search."""

from __future__ import annotations

import structlog

from app.agents.state import AgentLog, ContentAgentState
from app.services.llm_client import get_llm_client
from app.services.tavily_search import get_tavily_service

logger = structlog.get_logger(__name__)

RESEARCHER_SYSTEM = """You are an expert research analyst. Your job is to synthesize
web search results into clear, factual research notes that a content writer can use.

Focus on:
- Key facts and statistics
- Recent developments and trends
- Expert opinions and consensus views
- Counterarguments or alternative perspectives

Be concise but thorough. Cite sources when possible."""


async def researcher_node(state: ContentAgentState) -> dict:
    """Research the topic using Tavily and synthesize findings with Groq."""
    try:
        topic = state["topic"]
        content_type = state["content_type"]
        target_audience = state.get("target_audience", "general audience")

        logger.info("researcher_started", topic=topic)

        tavily = get_tavily_service()
        search_query = f"{topic} {content_type} for {target_audience}"
        raw_results = await tavily.search_formatted(search_query)

        llm = get_llm_client()
        user_prompt = f"""Topic: {topic}
Content Type: {content_type}
Target Audience: {target_audience}

Web Search Results:
{raw_results}

Synthesize these search results into structured research notes for a content writer.
Include key facts, trends, and angles to explore."""

        research_notes = await llm.generate(
            system_prompt=RESEARCHER_SYSTEM,
            user_prompt=user_prompt,
            temperature=0.3,
        )

        log_entry: AgentLog = {
            "agent": "researcher",
            "action": "completed_research",
            "summary": f"Researched '{topic}' — {len(research_notes)} chars of notes",
        }

        logger.info("researcher_completed", topic=topic)
        return {
            "research_notes": research_notes,
            "current_agent": "researcher",
            "agent_logs": [log_entry],
            "error": "",
        }
    except Exception as exc:
        logger.error("researcher_failed", error=str(exc))
        return {
            "current_agent": "researcher",
            "error": f"Researcher failed: {exc}",
            "agent_logs": [{
                "agent": "researcher",
                "action": "failed",
                "summary": str(exc),
            }],
        }
