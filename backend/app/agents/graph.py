"""LangGraph multi-agent orchestration graph."""

from __future__ import annotations

from typing import Literal

import structlog
from langgraph.graph import END, StateGraph

from app.agents.editor import editor_node
from app.agents.publisher import publisher_node
from app.agents.researcher import researcher_node
from app.agents.seo import seo_node
from app.agents.state import ContentAgentState
from app.agents.writer import writer_node

logger = structlog.get_logger(__name__)

NODE_STATUS_MAP = {
    "researcher": "researching",
    "writer": "writing",
    "seo": "seo",
    "editor": "quality_check",
    "publish": "publishing",
}


def _route_after_researcher(state: ContentAgentState) -> Literal["writer", "__end__"]:
    """Route after researcher node."""
    try:
        return "__end__" if state.get("error") else "writer"
    except Exception as exc:
        logger.error("routing_failed", error=str(exc))
        return "__end__"


def _route_after_writer(state: ContentAgentState) -> Literal["seo", "__end__"]:
    """Route after writer node."""
    try:
        return "__end__" if state.get("error") else "seo"
    except Exception as exc:
        logger.error("routing_failed", error=str(exc))
        return "__end__"


def _route_after_seo(state: ContentAgentState) -> Literal["__end__"]:
    """SEO is the last node in phase 1 (human review happens outside graph)."""
    return "__end__"


def _route_after_editor(state: ContentAgentState) -> Literal["publish", "__end__"]:
    """Route after quality check."""
    try:
        return "__end__" if state.get("error") else "publish"
    except Exception as exc:
        logger.error("routing_failed", error=str(exc))
        return "__end__"


def build_phase1_graph() -> StateGraph:
    """Build researcher → writer → seo pipeline (stops before human review)."""
    try:
        graph = StateGraph(ContentAgentState)
        graph.add_node("researcher", researcher_node)
        graph.add_node("writer", writer_node)
        graph.add_node("seo", seo_node)
        graph.set_entry_point("researcher")
        graph.add_conditional_edges("researcher", _route_after_researcher, {"writer": "writer", "__end__": END})
        graph.add_conditional_edges("writer", _route_after_writer, {"seo": "seo", "__end__": END})
        graph.add_edge("seo", END)
        return graph
    except Exception as exc:
        logger.error("phase1_graph_build_failed", error=str(exc))
        raise RuntimeError(f"Failed to build phase 1 graph: {exc}") from exc


def build_phase2_graph() -> StateGraph:
    """Build editor (quality check) → publisher pipeline."""
    try:
        graph = StateGraph(ContentAgentState)
        graph.add_node("editor", editor_node)
        graph.add_node("publish", publisher_node)
        graph.set_entry_point("editor")
        graph.add_conditional_edges("editor", _route_after_editor, {"publish": "publish", "__end__": END})
        graph.add_edge("publish", END)
        return graph
    except Exception as exc:
        logger.error("phase2_graph_build_failed", error=str(exc))
        raise RuntimeError(f"Failed to build phase 2 graph: {exc}") from exc


_phase1_graph = None
_phase2_graph = None


def _initial_state(
    job_id: str,
    topic: str,
    content_type: str,
    tone: str,
    brand_voice: str,
    target_audience: str,
    keywords: list[str],
    target_length: int,
    revision_feedback: str = "",
    research_notes: str = "",
    draft_content: str = "",
) -> ContentAgentState:
    """Build initial pipeline state."""
    return {
        "job_id": job_id,
        "topic": topic,
        "content_type": content_type,
        "tone": tone,
        "brand_voice": brand_voice,
        "target_audience": target_audience,
        "keywords": keywords,
        "target_length": target_length,
        "revision_feedback": revision_feedback,
        "research_notes": research_notes,
        "draft_content": draft_content,
        "final_content": "",
        "current_agent": "",
        "agent_logs": [],
        "error": "",
        "messages": [],
    }


async def run_phase1_pipeline(
    job_id: str,
    topic: str,
    content_type: str = "blog",
    tone: str = "professional",
    brand_voice: str = "professional",
    target_audience: str = "general audience",
    keywords: list[str] | None = None,
    target_length: int = 800,
    revision_feedback: str = "",
    research_notes: str = "",
    draft_content: str = "",
) -> ContentAgentState:
    """Run research → write → seo, then pause for human review."""
    global _phase1_graph
    try:
        if _phase1_graph is None:
            _phase1_graph = build_phase1_graph().compile()
        state = _initial_state(
            job_id, topic, content_type, tone, brand_voice,
            target_audience, keywords or [], target_length,
            revision_feedback, research_notes, draft_content,
        )
        result = await _phase1_graph.ainvoke(state)
        logger.info("phase1_completed", job_id=job_id)
        return result
    except Exception as exc:
        logger.error("phase1_failed", job_id=job_id, error=str(exc))
        raise RuntimeError(f"Phase 1 pipeline failed: {exc}") from exc


async def run_phase2_pipeline(state: ContentAgentState) -> ContentAgentState:
    """Run quality check → publish after human approval."""
    global _phase2_graph
    try:
        if _phase2_graph is None:
            _phase2_graph = build_phase2_graph().compile()
        result = await _phase2_graph.ainvoke(state)
        logger.info("phase2_completed", job_id=state["job_id"])
        return result
    except Exception as exc:
        logger.error("phase2_failed", job_id=state.get("job_id"), error=str(exc))
        raise RuntimeError(f"Phase 2 pipeline failed: {exc}") from exc


# Backward-compatible alias
async def run_content_pipeline(
    job_id: str,
    topic: str,
    content_type: str = "blog_post",
    tone: str = "professional",
    target_audience: str = "general audience",
) -> ContentAgentState:
    """Legacy full pipeline entry point."""
    return await run_phase1_pipeline(
        job_id=job_id,
        topic=topic,
        content_type=content_type,
        tone=tone,
        brand_voice=tone,
        target_audience=target_audience,
    )
