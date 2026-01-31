"""Tests for MCP handler implementations."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from museloop.config import MuseLoopConfig
from museloop.mcp.handlers import MCPHandlers
from museloop.mcp.job_state import JobState, JobStatus
from museloop.skills.base import BaseSkill, SkillInput, SkillOutput
from museloop.skills.registry import SkillRegistry


# --- Fixtures ---


class MockImageSkill(BaseSkill):
    name = "image_gen"
    description = "Mock image generation"

    async def execute(self, input: SkillInput, config: dict) -> SkillOutput:
        output_path = config.get("output_path", "/tmp/mock.png")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text("mock image")
        return SkillOutput(
            success=True,
            asset_paths=[output_path],
            metadata={"prompt": input.prompt},
        )


class MockAudioSkill(BaseSkill):
    name = "audio_gen"
    description = "Mock audio generation"

    async def execute(self, input: SkillInput, config: dict) -> SkillOutput:
        output_path = config.get("output_path", "/tmp/mock.wav")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text("mock audio")
        return SkillOutput(
            success=True,
            asset_paths=[output_path],
            metadata={"prompt": input.prompt},
        )


class FailingSkill(BaseSkill):
    name = "failing_skill"
    description = "Always fails"

    async def execute(self, input: SkillInput, config: dict) -> SkillOutput:
        raise RuntimeError("Skill execution failed")


@pytest.fixture
def mock_registry() -> SkillRegistry:
    registry = SkillRegistry()
    registry.register(MockImageSkill())
    registry.register(MockAudioSkill())
    return registry


@pytest.fixture
def handlers(tmp_path, mock_registry) -> MCPHandlers:
    config = MuseLoopConfig(
        anthropic_api_key="test-key",
        output_dir=str(tmp_path / "output"),
        prompts_dir=str(Path(__file__).parent.parent.parent / "prompts"),
    )
    return MCPHandlers(config=config, registry=mock_registry)


# --- JobState tests ---


class TestJobState:
    def test_initial_state(self):
        job = JobState(job_id="test123", brief={"task": "test"})
        assert job.status == JobStatus.PENDING
        assert job.iteration == 0
        assert job.assets == []
        assert job.events == []

    def test_add_event(self):
        job = JobState(job_id="test123", brief={"task": "test"})
        job.add_event("iteration_start", {"iteration": 1})
        assert len(job.events) == 1
        assert job.events[0]["event"] == "iteration_start"
        assert "timestamp" in job.events[0]

    def test_to_summary(self):
        job = JobState(
            job_id="abc",
            brief={"task": "test"},
            status=JobStatus.RUNNING,
            iteration=2,
            score=0.8,
        )
        summary = job.to_summary()
        assert summary["job_id"] == "abc"
        assert summary["status"] == "running"
        assert summary["iteration"] == 2
        assert summary["score"] == 0.8

    def test_status_enum_values(self):
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.AWAITING_APPROVAL.value == "awaiting_approval"


# --- MCPHandlers tests ---


class TestListSkills:
    def test_lists_registered_skills(self, handlers):
        skills = handlers.list_skills()
        names = [s["name"] for s in skills]
        assert "image_gen" in names
        assert "audio_gen" in names

    def test_returns_descriptions(self, handlers):
        skills = handlers.list_skills()
        for s in skills:
            assert "name" in s
            assert "description" in s


class TestGenerateImage:
    @pytest.mark.asyncio
    async def test_generates_image(self, handlers):
        result = await handlers.generate_image(prompt="A sunset")
        assert result["success"] is True
        assert len(result["asset_paths"]) > 0
        assert result["metadata"]["prompt"] == "A sunset"

    @pytest.mark.asyncio
    async def test_missing_skill_returns_error(self, handlers):
        handlers.registry = SkillRegistry()  # Empty registry
        result = await handlers.generate_image(prompt="test")
        assert result["success"] is False
        assert "not found" in result["error"]


class TestGenerateAudio:
    @pytest.mark.asyncio
    async def test_generates_audio(self, handlers):
        result = await handlers.generate_audio(prompt="Rain sounds")
        assert result["success"] is True
        assert len(result["asset_paths"]) > 0

    @pytest.mark.asyncio
    async def test_with_duration(self, handlers):
        result = await handlers.generate_audio(prompt="Thunder", duration_seconds=30)
        assert result["success"] is True


class TestSkillFailure:
    @pytest.mark.asyncio
    async def test_handles_execution_error(self, handlers):
        handlers.registry.register(FailingSkill())
        result = await handlers._execute_skill("failing_skill", prompt="test")
        assert result["success"] is False
        assert "failed" in result["error"].lower()


class TestJobManagement:
    def test_list_jobs_empty(self, handlers):
        assert handlers.list_jobs() == []

    def test_get_missing_job(self, handlers):
        result = handlers.get_job_status("nonexistent")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_run_pipeline_returns_job_id(self, handlers):
        with patch("museloop.mcp.handlers.MCPHandlers._run_pipeline_async", new_callable=AsyncMock):
            result = await handlers.run_pipeline(task="Test video")
            assert "job_id" in result
            assert result["status"] == "started"

    @pytest.mark.asyncio
    async def test_job_appears_in_list(self, handlers):
        with patch("museloop.mcp.handlers.MCPHandlers._run_pipeline_async", new_callable=AsyncMock):
            result = await handlers.run_pipeline(task="Test")
            jobs = handlers.list_jobs()
            assert len(jobs) == 1
            assert jobs[0]["job_id"] == result["job_id"]

    def test_approve_missing_job(self, handlers):
        result = handlers.approve_job("nonexistent")
        assert "error" in result

    def test_approve_wrong_status(self, handlers):
        job = JobState(job_id="test", brief={"task": "test"}, status=JobStatus.RUNNING)
        handlers._jobs["test"] = job
        result = handlers.approve_job("test")
        assert "error" in result
        assert "not awaiting" in result["error"].lower()

    def test_approve_awaiting_job(self, handlers):
        job = JobState(
            job_id="test",
            brief={"task": "test"},
            status=JobStatus.AWAITING_APPROVAL,
        )
        handlers._jobs["test"] = job
        result = handlers.approve_job("test", approved=True, notes="Looks good")
        assert result["approved"] is True
        assert len(job.events) == 1
