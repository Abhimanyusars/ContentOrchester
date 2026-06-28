"""WebSocket connection manager for live pipeline status."""

from __future__ import annotations

import asyncio
from typing import Any

import structlog
from fastapi import WebSocket

logger = structlog.get_logger(__name__)


class PipelineBroadcaster:
    """Manages WebSocket connections and broadcasts pipeline updates."""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, task_id: str, websocket: WebSocket) -> None:
        """Accept and register a WebSocket connection."""
        try:
            await websocket.accept()
            async with self._lock:
                self._connections.setdefault(task_id, []).append(websocket)
            logger.info("ws_connected", task_id=task_id)
        except Exception as exc:
            logger.error("ws_connect_failed", task_id=task_id, error=str(exc))
            raise RuntimeError(f"WebSocket connect failed: {exc}") from exc

    async def disconnect(self, task_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        try:
            async with self._lock:
                if task_id in self._connections:
                    self._connections[task_id] = [
                        ws for ws in self._connections[task_id] if ws != websocket
                    ]
                    if not self._connections[task_id]:
                        del self._connections[task_id]
            logger.info("ws_disconnected", task_id=task_id)
        except Exception as exc:
            logger.error("ws_disconnect_failed", task_id=task_id, error=str(exc))

    async def broadcast(self, task_id: str, payload: dict[str, Any]) -> None:
        """Broadcast a status update to all listeners for a task."""
        try:
            async with self._lock:
                sockets = list(self._connections.get(task_id, []))
            dead: list[WebSocket] = []
            for ws in sockets:
                try:
                    await ws.send_json(payload)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                await self.disconnect(task_id, ws)
        except Exception as exc:
            logger.error("ws_broadcast_failed", task_id=task_id, error=str(exc))


broadcaster = PipelineBroadcaster()
