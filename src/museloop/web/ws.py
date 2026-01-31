"""WebSocket endpoint for real-time pipeline progress events."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from starlette.websockets import WebSocket, WebSocketDisconnect

from museloop.utils.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasts events."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self._connections.append(websocket)
        logger.info("ws_connected", count=len(self._connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            if websocket in self._connections:
                self._connections.remove(websocket)
        logger.info("ws_disconnected", count=len(self._connections))

    def broadcast_sync(self, event: str, data: dict[str, Any]) -> None:
        """Synchronous broadcast (called from event callbacks).

        Schedules async sends on the event loop.
        """
        message = json.dumps({"event": event, "data": data}, default=str)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._broadcast_async(message))
        except RuntimeError:
            pass  # No event loop running

    async def _broadcast_async(self, message: str) -> None:
        """Send a message to all connected clients."""
        async with self._lock:
            dead: list[WebSocket] = []
            for ws in self._connections:
                try:
                    await ws.send_text(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._connections.remove(ws)


async def websocket_endpoint(websocket: WebSocket, manager: ConnectionManager) -> None:
    """WebSocket endpoint handler."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; client can send pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
