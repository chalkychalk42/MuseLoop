"""Tests for web API routes."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from museloop.config import MuseLoopConfig
from museloop.mcp.job_state import JobState, JobStatus
from museloop.web.app import create_app
from museloop.web.job_manager import JobManager


@pytest.fixture
def config(tmp_path) -> MuseLoopConfig:
    return MuseLoopConfig(
        anthropic_api_key="test-key",
        output_dir=str(tmp_path / "output"),
        prompts_dir=str(Path(__file__).parent.parent.parent / "prompts"),
    )


@pytest.fixture
def app(config):
    return create_app(config)


@pytest.fixture
def client(app):
    return TestClient(app)


class TestSkillsEndpoint:
    def test_list_skills(self, client):
        resp = client.get("/api/skills")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Should have discovered skills from manifests
        names = [s["name"] for s in data]
        assert "image_gen" in names


class TestJobsEndpoint:
    def test_list_jobs_empty(self, client):
        resp = client.get("/api/jobs")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_job(self, client):
        with patch.object(JobManager, "_run_job", new_callable=AsyncMock):
            resp = client.post("/api/jobs", json={
                "task": "Test video",
                "style": "cyberpunk",
            })
            assert resp.status_code == 200
            data = resp.json()
            assert "job_id" in data
            assert data["status"] in ("pending", "running")

    def test_get_missing_job(self, client):
        resp = client.get("/api/jobs/nonexistent")
        assert resp.status_code == 404

    def test_get_job_after_create(self, client):
        with patch.object(JobManager, "_run_job", new_callable=AsyncMock):
            create_resp = client.post("/api/jobs", json={"task": "Test"})
            job_id = create_resp.json()["job_id"]

            resp = client.get(f"/api/jobs/{job_id}")
            assert resp.status_code == 200
            assert resp.json()["job_id"] == job_id


class TestApprovalEndpoint:
    def test_approve_nonexistent_job(self, client):
        resp = client.post("/api/jobs/fake/approve", json={"approved": True})
        assert resp.status_code == 400

    def test_approve_running_job_fails(self, client):
        with patch.object(JobManager, "_run_job", new_callable=AsyncMock):
            create_resp = client.post("/api/jobs", json={"task": "Test"})
            job_id = create_resp.json()["job_id"]

            resp = client.post(f"/api/jobs/{job_id}/approve", json={"approved": True})
            assert resp.status_code == 400


class TestAssetEndpoint:
    def test_missing_asset(self, client):
        resp = client.get("/api/assets/nonexistent.png")
        assert resp.status_code == 404

    def test_traversal_rejected(self, client):
        resp = client.get("/api/assets/../../../etc/passwd")
        # Either 400 (traversal caught) or 404 (path doesn't exist) is safe
        assert resp.status_code in (400, 404)


class TestStaticFiles:
    def test_index_serves(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "MuseLoop" in resp.text
