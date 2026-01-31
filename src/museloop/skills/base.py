"""Base skill class and I/O models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, Field


class SkillInput(BaseModel):
    """Input for a skill execution."""

    prompt: str = Field(..., description="The generation prompt")
    params: dict[str, Any] = Field(default_factory=dict, description="Additional parameters")


class SkillOutput(BaseModel):
    """Output from a skill execution."""

    success: bool = True
    asset_paths: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class BaseSkill(ABC):
    """Abstract base class for pluggable multimedia skills.

    To create a new skill:
    1. Subclass BaseSkill
    2. Implement execute()
    3. Create a manifest JSON in skills/manifests/
    """

    name: str = "base"
    description: str = "Base skill"

    @abstractmethod
    async def execute(self, input: SkillInput, config: dict[str, Any]) -> SkillOutput:
        """Execute the skill. Returns paths to generated assets."""
        ...
