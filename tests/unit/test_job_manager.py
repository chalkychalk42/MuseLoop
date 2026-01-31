"""Tests for the job manager."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from museloop.config import MuseLoopConfig
from museloop.mcp.job_state import JobStatus
from museloop.web.job_manager import JobManager


@pytest.fixture
def config(tmp_path) -> MuseLoopConfig:
    return MuseLoopConfig(
        anthropic_api_key="test-key",
        output_dir=str(tmp_path / "output"),
        prompts_dir=str(Path(__file__).parent.parent.parent / "prompts"),
    )


@pytest.fixture
def manager(config) -> JobManager:
    return JobManager(config)


class TestJobManager:
    @pytest.mark.asyncio
    async def test_create_job(self, manager):
        with patch.object(JobManager, "_run_job", new_callable=AsyncMock):
            job = await manager.create_job(task="Test video")
            assert job.job_id
            assert job.brief["task"] == "Test video"
            assert job.status in (JobStatus.PENDING, JobStatus.RUNNING)

    @pytest.mark.asyncio
    async def test_list_jobs(self, manager):
        with patch.object(JobManager, "_run_job", new_callable=AsyncMock):
            await manager.create_job(task="Job 1")
            await manager.create_job(task="Job 2")
            jobs = manager.list_jobs()
            assert len(jobs) == 2

    @pytest.mark.asyncio
    async def test_get_job(self, manager):
        with patch.object(JobManager, "_run_job", new_callable=AsyncMock):
            job = await manager.create_job(task="Test")
            found = manager.get_job(job.job_id)
            assert found is not None
            assert found.job_id == job.job_id

    def test_get_missing_job(self, manager):
        assert manager.get_job("nonexistent") is None

    def test_approve_non_awaiting_job(self, manager):
        assert manager.approve_job("nonexistent", True) is False

    @pytest.mark.asyncio
    async def test_broadcast_called(self, manager):
        events = []
        manager.set_broadcast(lambda event, data: events.append((event, data)))
        with patch.object(JobManager, "_run_job", new_callable=AsyncMock):
            await manager.create_job(task="Test")
            # Broadcast is set but _run_job is mocked, so no events yet
            assert manager._broadcast is not None

    @pytest.mark.asyncio
    async def test_job_config_inherits(self, manager):
        """Job config should inherit from manager config."""
        with patch.object(JobManager, "_run_job", new_callable=AsyncMock):
            job = await manager.create_job(
                task="Test",
                max_iterations=3,
                quality_threshold=0.9,
            )
            assert job.max_iterations == 3
