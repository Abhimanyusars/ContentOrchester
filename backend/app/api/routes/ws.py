"""WebSocket routes for live pipeline status."""

from __future__ import annotations

import asyncio

import uuid

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.database import get_session_factory
from app.services.brief_service import BriefService
from app.services.pipeline_broadcaster import broadcaster

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["websocket"])


@router.websocket("/ws/{task_id}")
async def pipeline_status_ws(task_id: str, websocket: WebSocket) -> None:
    """Stream live pipeline status updates for a task."""
    try:
        await broadcaster.connect(task_id, websocket)

        session_factory = get_session_factory()
        async with session_factory() as session:
            service = BriefService(session)
            job = await service.get_job(uuid.UUID(task_id))
            if job:
                await websocket.send_json({
                    "task_id": task_id,
                    "status": job.status.value,
                    "current_node": job.current_node,
                    "message": "Connected",
                })

        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        await broadcaster.disconnect(task_id, websocket)
    except Exception as exc:
        logger.error("ws_error", task_id=task_id, error=str(exc))
        await broadcaster.disconnect(task_id, websocket)
