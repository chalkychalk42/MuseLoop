"""Brief: the creative task specification that drives the pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


class Brief(BaseModel):
    """A creative task specification. JSON input that drives the entire pipeline."""

    task: str = Field(..., description="The creative task to accomplish")
    style: Optional[str] = Field(None, description="Visual/creative style")
    duration_seconds: Optional[int] = Field(None, description="Target duration for video/audio")
    skills_required: list[str] = Field(
        default_factory=list, description="Skills to use (e.g., image_gen, audio_gen)"
    )
    constraints: dict[str, Any] = Field(
        default_factory=dict, description="Additional constraints (e.g., aspect_ratio)"
    )
    reference_assets: list[str] = Field(
        default_factory=list, description="Paths to reference files"
    )

    @classmethod
    def from_file(cls, path: str | Path) -> Brief:
        """Load and validate a brief from a JSON file."""
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Brief file not found: {file_path}")
        if not file_path.suffix == ".json":
            raise ValueError(f"Brief must be a JSON file, got: {file_path.suffix}")
        data = json.loads(file_path.read_text())
        return cls(**data)

    def summary(self) -> str:
        """Return a human-readable summary of the brief."""
        parts = [f"Task: {self.task}"]
        if self.style:
            parts.append(f"Style: {self.style}")
        if self.duration_seconds:
            parts.append(f"Duration: {self.duration_seconds}s")
        if self.skills_required:
            parts.append(f"Skills: {', '.join(self.skills_required)}")
        if self.constraints:
            parts.append(f"Constraints: {self.constraints}")
        return " | ".join(parts)
