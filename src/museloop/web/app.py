"""FastAPI application — mounts routes, static files, and WebSocket."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from starlette.websockets import WebSocket

from museloop.config import MuseLoopConfig
from museloop.skills.registry import SkillRegistry
from museloop.web.job_manager import JobManager
from museloop.web.routes import router, set_dependencies
from museloop.web.ws import ConnectionManager, websocket_endpoint

_STATIC_DIR = Path(__file__).parent / "static"


def create_app(config: MuseLoopConfig | None = None) -> FastAPI:
    """Build the FastAPI application with all routes and dependencies."""
    config = config or MuseLoopConfig()

    app = FastAPI(
        title="MuseLoop Dashboard",
        description="Web dashboard for MuseLoop creative pipelines",
        version="0.1.0",
    )

    # Initialize shared services
    registry = SkillRegistry()
    registry.discover()

    ws_manager = ConnectionManager()
    job_manager = JobManager(config)
    job_manager.set_broadcast(ws_manager.broadcast_sync)

    # Inject dependencies into routes
    set_dependencies(job_manager, registry)

    # Mount API routes
    app.include_router(router)

    # WebSocket endpoint
    @app.websocket("/ws")
    async def ws_route(websocket: WebSocket) -> None:
        await websocket_endpoint(websocket, ws_manager)

    # Serve static files (SPA)
    if _STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

        @app.get("/")
        async def index() -> FileResponse:
            return FileResponse(str(_STATIC_DIR / "index.html"))

    return app
