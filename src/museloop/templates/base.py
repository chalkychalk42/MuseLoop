"""Workflow template model and brief conversion."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class TemplateStep(BaseModel):
    """A single step in a workflow template."""

    order: int
    skill: str
    description: str
    params: dict[str, Any] = Field(default_factory=dict)


class ExportSettings(BaseModel):
    """Export configuration for a template."""

    aspect_ratio: str = "16:9"
    resolution: str = "1920x1080"
    fps: int = 30
    codec: str = "h264"


class WorkflowTemplate(BaseModel):
    """Defines a reusable workflow template."""

    name: str
    category: str
    description: str
    default_style: str = ""
    default_skills: list[str] = Field(default_factory=list)
    steps: list[TemplateStep] = Field(default_factory=list)
    export: ExportSettings = Field(default_factory=ExportSettings)
    duration_range: tuple[int, int] = (30, 60)
    constraints: dict[str, Any] = Field(default_factory=dict)

    def to_brief(self, task: str, style: str | None = None) -> dict[str, Any]:
        """Convert template + user task into a full brief dict."""
        resolved_style = style or self.default_style
        duration = (self.duration_range[0] + self.duration_range[1]) // 2

        return {
            "task": task,
            "style": resolved_style,
            "duration_seconds": duration,
            "skills_required": self.default_skills,
            "constraints": {
                "aspect_ratio": self.export.aspect_ratio,
                "resolution": self.export.resolution,
                "fps": self.export.fps,
                **self.constraints,
            },
            "reference_assets": [],
            "template": self.name,
        }
