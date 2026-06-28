"""LangGraph agent state definition."""

from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentLog(TypedDict):
    """Single agent activity log entry."""

    agent: str
    action: str
    summary: str


class ContentAgentState(TypedDict):
    """Shared state passed between agents in the LangGraph pipeline."""

    job_id: str
    topic: str
    content_type: str
    tone: str
    brand_voice: str
    target_audience: str
    keywords: list[str]
    target_length: int
    revision_feedback: str
    research_notes: str
    draft_content: str
    final_content: str
    current_agent: str
    agent_logs: Annotated[list[AgentLog], lambda a, b: a + b]
    error: str
    messages: Annotated[list, add_messages]
