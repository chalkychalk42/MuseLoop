"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from museloop.config import MuseLoopConfig
from museloop.llm.base import LLMBackend
from museloop.skills.base import BaseSkill, SkillInput, SkillOutput
from museloop.skills.registry import SkillRegistry


@pytest.fixture
def mock_llm() -> AsyncMock:
    """Returns a mock LLM that returns predictable JSON responses."""
    llm = AsyncMock(spec=LLMBackend)
    llm.generate = AsyncMock(
        return_value='{"plan": [{"step": 1, "task": "test image", "skill": "image_gen", "params": {"prompt": "test"}}], "script": "A test script"}'
    )
    return llm


@pytest.fixture
def sample_brief_dict() -> dict:
    return {
        "task": "Test trailer",
        "style": "cyberpunk",
        "duration_seconds": 30,
        "skills_required": ["image_gen"],
        "constraints": {"aspect_ratio": "16:9"},
        "reference_assets": [],
    }


@pytest.fixture
def sample_brief_path(tmp_path: Path, sample_brief_dict: dict) -> Path:
    import json

    path = tmp_path / "test_brief.json"
    path.write_text(json.dumps(sample_brief_dict))
    return path


@pytest.fixture
def config(tmp_path: Path) -> MuseLoopConfig:
    return MuseLoopConfig(
        anthropic_api_key="test-key",
        output_dir=str(tmp_path / "output"),
        prompts_dir=str(Path(__file__).parent.parent / "prompts"),
        max_iterations=2,
        quality_threshold=0.7,
    )


class MockSkill(BaseSkill):
    name = "mock_skill"
    description = "A mock skill for testing"

    async def execute(self, input: SkillInput, config: dict) -> SkillOutput:
        output_path = config.get("output_path", "/tmp/mock_output.png")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text("mock content")
        return SkillOutput(
            success=True,
            asset_paths=[output_path],
            metadata={"source": "mock"},
        )


@pytest.fixture
def mock_registry() -> SkillRegistry:
    registry = SkillRegistry()
    registry.register(MockSkill())
    return registry
