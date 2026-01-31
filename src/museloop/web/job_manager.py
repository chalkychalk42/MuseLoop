"""Job lifecycle management — shared between Web and MCP interfaces."""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any, Callable

from museloop.config import MuseLoopConfig
from museloop.mcp.job_state import JobState, JobStatus
from museloop.utils.logging import get_logger

logger = get_logger(__name__)

# Type for WebSocket broadcast
EventBroadcast = Callable[[str, dict[str, Any]], None]


class JobManager:
    """Manages pipeline job lifecycle with event broadcasting."""

    def __init__(self, config: MuseLoopConfig) -> None:
        self.config = config
        self._jobs: dict[str, JobState] = {}
        self._tasks: dict[str, asyncio.Task[Any]] = {}
        self._broadcast: EventBroadcast | None = None

    def set_broadcast(self, broadcast: EventBroadcast) -> None:
        """Register a callback for broadcasting events (e.g., WebSocket)."""
        self._broadcast = broadcast

    async def create_job(
        self,
        task: str,
        style: str = "",
        max_iterations: int | None = None,
        quality_threshold: float | None = None,
    ) -> JobState:
        """Create and start a new pipeline job."""
        job_id = uuid.uuid4().hex[:12]
        brief = {
            "task": task,
            "style": style,
            "duration_seconds": 30,
            "skills_required": [],
            "constraints": {},
            "reference_assets": [],
        }

        job_config = MuseLoopConfig(
            anthropic_api_key=self.config.anthropic_api_key,
            llm_backend=self.config.llm_backend,
            output_dir=str(Path(self.config.output_dir) / job_id),
            prompts_dir=self.config.prompts_dir,
            max_iterations=max_iterations or self.config.max_iterations,
            quality_threshold=quality_threshold or self.config.quality_threshold,
            comfyui_url=self.config.comfyui_url,
            replicate_api_key=self.config.replicate_api_key,
        )

        job = JobState(
            job_id=job_id,
            brief=brief,
            max_iterations=job_config.max_iterations,
            output_dir=job_config.output_dir,
        )
        self._jobs[job_id] = job

        self._tasks[job_id] = asyncio.create_task(
            self._run_job(job, job_config)
        )

        return job

    async def _run_job(self, job: JobState, config: MuseLoopConfig) -> None:
        """Execute the pipeline for a job."""
        from museloop.core.loop import run_loop

        output_path = Path(config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        brief_path = output_path / "brief.json"
        brief_path.write_text(json.dumps(job.brief))

        def on_event(event: str, data: dict[str, Any]) -> None:
            job.add_event(event, data)
            if event == "iteration_start":
                job.iteration = data.get("iteration", 0)
                job.status = JobStatus.RUNNING
            elif event == "iteration_complete":
                job.score = data.get("score", 0.0)
                job.best_score = data.get("best_score", 0.0)
                job.best_iteration = data.get("best_iteration", 0)

            # Broadcast to WebSocket clients
            if self._broadcast:
                self._broadcast(event, {"job_id": job.job_id, **data})

        try:
            job.status = JobStatus.RUNNING
            await run_loop(str(brief_path), config, on_event=on_event)
            job.status = JobStatus.COMPLETED
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            logger.error("job_failed", job_id=job.job_id, error=str(e))
        finally:
            import time

            job.completed_at = time.time()
            if self._broadcast:
                self._broadcast("job_finished", job.to_summary())

    def get_job(self, job_id: str) -> JobState | None:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[dict[str, Any]]:
        """List all jobs as summaries."""
        return [job.to_summary() for job in self._jobs.values()]

    def approve_job(self, job_id: str, approved: bool, notes: str = "") -> bool:
        """Approve or reject a job awaiting human approval."""
        job = self._jobs.get(job_id)
        if not job or job.status != JobStatus.AWAITING_APPROVAL:
            return False
        job.add_event("human_approval", {"approved": approved, "notes": notes})
        return True
