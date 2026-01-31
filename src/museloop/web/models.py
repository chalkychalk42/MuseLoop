"""Pydantic request/response models for the web API."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class JobCreateRequest(BaseModel):
    """Request to create a new pipeline job."""

    task: str = Field(..., description="What to create")
    style: str = Field(default="", description="Visual/audio style")
    max_iterations: int = Field(default=5, ge=1, le=20)
    quality_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class JobSummary(BaseModel):
    """Summary of a pipeline job."""

    job_id: str
    status: str
    iteration: int = 0
    max_iterations: int = 5
    score: float = 0.0
    best_score: float = 0.0
    best_iteration: int = 0
    asset_count: int = 0
    error: Optional[str] = None
    output_dir: Optional[str] = None


class ApproveRequest(BaseModel):
    """Request to approve or reject a job."""

    approved: bool = True
    notes: str = ""


class SkillInfo(BaseModel):
    """Skill information."""

    name: str
    description: str


class AssetInfo(BaseModel):
    """Asset information."""

    path: str
    iteration: int = 0
    type: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
