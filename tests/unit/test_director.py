"""Tests for DirectorAgent."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from museloop.agents.director import DirectorAgent
from museloop.skills.base import BaseSkill, SkillInput, SkillOutput
from museloop.skills.registry import SkillRegistry


class FakeImageSkill(BaseSkill):
    name = "image_gen"
    description = "Fake image skill"

    async def execute(self, input: SkillInput, config: dict) -> SkillOutput:
        output_path = config.get("output_path", "/tmp/fake.png")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text("fake image")
        return SkillOutput(
            success=True,
            asset_paths=[output_path],
            metadata={"source": "fake"},
        )


class FailingSkill(BaseSkill):
    name = "failing_skill"
    description = "Always fails"

    async def execute(self, input: SkillInput, config: dict) -> SkillOutput:
        return SkillOutput(success=False, error="Intentional failure")


@pytest.fixture
def director_registry():
    registry = SkillRegistry()
    registry.register(FakeImageSkill())
    registry.register(FailingSkill())
    return registry


@pytest.fixture
def director_state():
    return {
        "brief": {"task": "Test trailer", "style": "cyberpunk"},
        "iteration": 1,
        "plan": [
            {"step": 1, "task": "hero shot", "skill": "image_gen", "params": {"prompt": "neon city"}},
        ],
        "assets": [],
        "critique": {},
        "messages": [],
        "memory": {},
        "status": "generating",
    }


@pytest.mark.asyncio
async def test_director_executes_plan(mock_llm, director_registry, director_state, tmp_path):
    agent = DirectorAgent(
        mock_llm, prompts_dir="./prompts",
        registry=director_registry, output_dir=str(tmp_path),
    )
    result = await agent.run(director_state)
    assert "assets" in result
    assert len(result["assets"]) == 1
    assert result["assets"][0]["type"] == "image"
    assert result["status"] == "critiquing"


@pytest.mark.asyncio
async def test_director_empty_plan(mock_llm, director_registry, director_state, tmp_path):
    director_state["plan"] = []
    agent = DirectorAgent(
        mock_llm, prompts_dir="./prompts",
        registry=director_registry, output_dir=str(tmp_path),
    )
    result = await agent.run(director_state)
    assert result["assets"] == []
    assert "No plan" in result["messages"][0]["content"]


@pytest.mark.asyncio
async def test_director_skips_missing_skill(mock_llm, director_registry, director_state, tmp_path):
    director_state["plan"] = [
        {"step": 1, "task": "test", "skill": "nonexistent_skill", "params": {}},
    ]
    agent = DirectorAgent(
        mock_llm, prompts_dir="./prompts",
        registry=director_registry, output_dir=str(tmp_path),
    )
    result = await agent.run(director_state)
    assert result["assets"] == []


@pytest.mark.asyncio
async def test_director_handles_skill_failure(mock_llm, director_registry, director_state, tmp_path):
    director_state["plan"] = [
        {"step": 1, "task": "fail", "skill": "failing_skill", "params": {"prompt": "fail"}},
    ]
    agent = DirectorAgent(
        mock_llm, prompts_dir="./prompts",
        registry=director_registry, output_dir=str(tmp_path),
    )
    result = await agent.run(director_state)
    # Failing skill raises RuntimeError, caught by gather(return_exceptions=True)
    assert result["assets"] == []


@pytest.mark.asyncio
async def test_director_parallel_execution(mock_llm, director_registry, director_state, tmp_path):
    director_state["plan"] = [
        {"step": 1, "task": "shot 1", "skill": "image_gen", "params": {"prompt": "a"}},
        {"step": 2, "task": "shot 2", "skill": "image_gen", "params": {"prompt": "b"}},
    ]
    agent = DirectorAgent(
        mock_llm, prompts_dir="./prompts",
        registry=director_registry, output_dir=str(tmp_path),
    )
    result = await agent.run(director_state)
    assert len(result["assets"]) == 2
