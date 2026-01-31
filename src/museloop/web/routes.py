"""FastAPI REST endpoints for the web dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from starlette.responses import FileResponse

from museloop.web.models import ApproveRequest, JobCreateRequest, JobSummary

router = APIRouter(prefix="/api")

# These are set by app.py during startup
_job_manager: Any = None
_skill_registry: Any = None


def set_dependencies(job_manager: Any, skill_registry: Any) -> None:
    """Inject dependencies (called during app setup)."""
    global _job_manager, _skill_registry
    _job_manager = job_manager
    _skill_registry = skill_registry


@router.post("/jobs", response_model=JobSummary)
async def create_job(request: JobCreateRequest) -> dict[str, Any]:
    """Submit a new pipeline job."""
    job = await _job_manager.create_job(
        task=request.task,
        style=request.style,
        max_iterations=request.max_iterations,
        quality_threshold=request.quality_threshold,
    )
    return job.to_summary()


@router.get("/jobs")
async def list_jobs() -> list[dict[str, Any]]:
    """List all pipeline jobs."""
    return _job_manager.list_jobs()


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict[str, Any]:
    """Get details of a specific job."""
    job = _job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job.to_summary()


@router.get("/jobs/{job_id}/assets")
async def get_job_assets(job_id: str) -> list[dict[str, Any]]:
    """List assets for a specific job."""
    job = _job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job.assets


@router.post("/jobs/{job_id}/approve")
async def approve_job(job_id: str, request: ApproveRequest) -> dict[str, str]:
    """Approve or reject a job awaiting human review."""
    success = _job_manager.approve_job(job_id, request.approved, request.notes)
    if not success:
        raise HTTPException(status_code=400, detail="Job not awaiting approval")
    return {"status": "approved" if request.approved else "rejected"}


@router.get("/skills")
async def list_skills() -> list[dict[str, str]]:
    """List all available skills."""
    if _skill_registry is None:
        return []
    return _skill_registry.list_details()


@router.get("/assets/{path:path}")
async def serve_asset(path: str) -> FileResponse:
    """Serve a generated asset file."""
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Asset not found")
    # Basic security check
    if ".." in file_path.parts:
        raise HTTPException(status_code=400, detail="Invalid path")
    return FileResponse(file_path)
