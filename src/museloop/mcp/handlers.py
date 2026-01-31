"""MCP tool handler implementations — dispatches to MuseLoop skills and pipeline."""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any

from museloop.config import MuseLoopConfig
from museloop.mcp.job_state import JobState, JobStatus
from museloop.skills.base import SkillInput
from museloop.skills.registry import SkillRegistry
from museloop.utils.logging import get_logger

logger = get_logger(__name__)


class MCPHandlers:
    """Stateful handler class that holds registry, config, and active jobs."""

    def __init__(
        self,
        config: MuseLoopConfig | None = None,
        registry: SkillRegistry | None = None,
    ) -> None:
        self.config = config or MuseLoopConfig()
        self.registry = registry or SkillRegistry()
        if registry is None:
            self.registry.discover()
        self._jobs: dict[str, JobState] = {}
        self._job_tasks: dict[str, asyncio.Task[Any]] = {}

    # --- Pipeline ---

    async def run_pipeline(
        self,
        task: str,
        style: str = "",
        max_iterations: int | None = None,
        quality_threshold: float | None = None,
    ) -> dict[str, Any]:
        """Start a full pipeline run in the background. Returns job ID."""
        job_id = uuid.uuid4().hex[:12]
        brief = {
            "task": task,
            "style": style,
            "duration_seconds": 30,
            "skills_required": self.registry.list_skills(),
            "constraints": {},
            "reference_assets": [],
        }

        config = MuseLoopConfig(
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
            max_iterations=config.max_iterations,
            output_dir=config.output_dir,
        )
        self._jobs[job_id] = job

        # Launch pipeline in background task
        self._job_tasks[job_id] = asyncio.create_task(
            self._run_pipeline_async(job, brief, config)
        )

        return {"job_id": job_id, "status": "started"}

    async def _run_pipeline_async(
        self,
        job: JobState,
        brief: dict[str, Any],
        config: MuseLoopConfig,
    ) -> None:
        """Execute the pipeline, updating job state with events."""
        from museloop.core.loop import run_loop

        # Write brief to temp file for run_loop
        output_path = Path(config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        brief_path = output_path / "brief.json"
        brief_path.write_text(json.dumps(brief))

        def on_event(event: str, data: dict[str, Any]) -> None:
            job.add_event(event, data)
            if event == "iteration_start":
                job.iteration = data.get("iteration", 0)
                job.status = JobStatus.RUNNING
            elif event == "iteration_complete":
                job.score = data.get("score", 0.0)
                job.best_score = data.get("best_score", 0.0)
                job.best_iteration = data.get("best_iteration", 0)
            elif event == "loop_complete":
                job.assets = [
                    {"iteration": a.get("iteration", 0), "path": a.get("path", "")}
                    for a in data.get("assets", [])
                ]

        try:
            job.status = JobStatus.RUNNING
            await run_loop(str(brief_path), config, on_event=on_event)
            job.status = JobStatus.COMPLETED
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            logger.error("pipeline_failed", job_id=job.job_id, error=str(e))
        finally:
            import time

            job.completed_at = time.time()

    # --- Single skill execution ---

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
    ) -> dict[str, Any]:
        """Generate a single image using the image_gen skill."""
        return await self._execute_skill(
            "image_gen",
            prompt=prompt,
            params={"negative_prompt": negative_prompt, "width": width, "height": height},
        )

    async def generate_audio(
        self,
        prompt: str,
        duration_seconds: int = 10,
    ) -> dict[str, Any]:
        """Generate audio using the audio_gen skill."""
        return await self._execute_skill(
            "audio_gen",
            prompt=prompt,
            params={"duration_seconds": duration_seconds},
        )

    async def _execute_skill(
        self, skill_name: str, prompt: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a single skill and return its output."""
        if not self.registry.has(skill_name):
            return {"error": f"Skill '{skill_name}' not found", "success": False}

        skill = self.registry.get(skill_name)
        skill_input = SkillInput(prompt=prompt, params=params or {})

        output_path = Path(self.config.output_dir) / "mcp_outputs"
        output_path.mkdir(parents=True, exist_ok=True)

        skill_config = {
            "output_path": str(output_path / f"{skill_name}_{uuid.uuid4().hex[:8]}"),
            "comfyui_url": self.config.comfyui_url or "http://localhost:8188",
            "replicate_api_key": self.config.replicate_api_key,
        }

        try:
            result = await skill.execute(skill_input, skill_config)
            return {
                "success": result.success,
                "asset_paths": result.asset_paths,
                "metadata": result.metadata,
                "error": result.error,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Query tools ---

    def list_skills(self) -> list[dict[str, str]]:
        """List all available skills."""
        return self.registry.list_details()

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        """Get the current status of a pipeline job."""
        job = self._jobs.get(job_id)
        if not job:
            return {"error": f"Job '{job_id}' not found"}
        return job.to_summary()

    def list_jobs(self) -> list[dict[str, Any]]:
        """List all jobs."""
        return [job.to_summary() for job in self._jobs.values()]

    def approve_job(self, job_id: str, approved: bool = True, notes: str = "") -> dict[str, Any]:
        """Resolve human-in-the-loop approval for a job."""
        job = self._jobs.get(job_id)
        if not job:
            return {"error": f"Job '{job_id}' not found"}
        if job.status != JobStatus.AWAITING_APPROVAL:
            return {"error": f"Job is not awaiting approval (status: {job.status.value})"}

        job.add_event("human_approval", {"approved": approved, "notes": notes})
        return {"job_id": job_id, "approved": approved}
