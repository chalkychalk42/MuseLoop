"""DirectorAgent: orchestrates skill execution based on the plan."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from museloop.agents.base import BaseAgent, logger
from museloop.core.state import LoopState
from museloop.llm.base import LLMBackend
from museloop.skills.registry import SkillRegistry
from museloop.utils.file_io import asset_path

# Limit concurrent skill executions to prevent resource exhaustion
_DEFAULT_MAX_CONCURRENT = 4


class DirectorAgent(BaseAgent):
    agent_name = "director"
    prompt_file = "director_agent.md"

    def __init__(
        self,
        llm: LLMBackend,
        prompts_dir: str,
        registry: SkillRegistry,
        output_dir: str,
        max_concurrent: int = _DEFAULT_MAX_CONCURRENT,
    ):
        super().__init__(llm, prompts_dir)
        self.registry = registry
        self.output_dir = output_dir
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def run(self, state: LoopState) -> dict[str, Any]:
        logger.info("director_agent_start", iteration=state["iteration"])

        plan = state.get("plan", [])
        iteration = state["iteration"]

        if not plan:
            return {
                "assets": [],
                "status": "critiquing",
                "messages": [
                    {
                        "role": "assistant",
                        "content": "[DirectorAgent] No plan to execute.",
                    }
                ],
            }

        # Group tasks by independence for parallel execution
        assets = []
        execution_log = []

        # Execute tasks — parallel where possible
        tasks_to_run = []
        for task in plan:
            skill_name = task.get("skill", "")
            if self.registry.has(skill_name):
                tasks_to_run.append(task)
            else:
                execution_log.append(f"Skipped step {task.get('step')}: skill '{skill_name}' not available")
                logger.warning("skill_not_found", skill=skill_name, step=task.get("step"))

        # Run all available tasks concurrently
        if tasks_to_run:
            results = await asyncio.gather(
                *[self._execute_task(task, iteration) for task in tasks_to_run],
                return_exceptions=True,
            )

            for task, result in zip(tasks_to_run, results):
                if isinstance(result, Exception):
                    execution_log.append(
                        f"Step {task.get('step')} failed: {result}"
                    )
                    logger.error("task_execution_failed", step=task.get("step"), error=str(result))
                elif result:
                    assets.append(result)
                    execution_log.append(
                        f"Step {task.get('step')} completed: {result.get('path', 'no path')}"
                    )

        return {
            "assets": assets,
            "status": "critiquing",
            "director_retries": state.get("director_retries", 0) + (0 if assets else 1),
            "messages": [
                {
                    "role": "assistant",
                    "content": (
                        f"[DirectorAgent] Executed {len(assets)}/{len(plan)} tasks. "
                        f"Log: {'; '.join(execution_log[:5])}"
                    ),
                }
            ],
        }

    async def _execute_task(self, task: dict[str, Any], iteration: int) -> dict[str, Any]:
        """Execute a single task using the appropriate skill (with concurrency limit)."""
        async with self._semaphore:
            return await self._execute_task_inner(task, iteration)

    async def _execute_task_inner(self, task: dict[str, Any], iteration: int) -> dict[str, Any]:
        """Inner task execution logic."""
        from museloop.skills.base import SkillInput

        skill_name = task["skill"]
        skill = self.registry.get(skill_name)
        params = task.get("params", {})

        # Build skill input
        skill_input = SkillInput(
            prompt=params.get("prompt", task.get("task", "")),
            params=params,
        )

        # Determine output path
        step = task.get("step", 0)
        ext_map = {"image_gen": "png", "video_gen": "mp4", "audio_gen": "wav", "editing": "mp4"}
        ext = ext_map.get(skill_name, "bin")
        output_path = asset_path(self.output_dir, iteration, f"step-{step:03d}-{skill_name}", ext)

        # Execute the skill
        output = await skill.execute(skill_input, {"output_path": str(output_path)})

        if output.success:
            return {
                "type": skill_name.replace("_gen", ""),
                "path": output.asset_paths[0] if output.asset_paths else str(output_path),
                "step": step,
                "metadata": {
                    "prompt_used": skill_input.prompt,
                    "skill": skill_name,
                    **output.metadata,
                },
            }
        else:
            raise RuntimeError(f"Skill {skill_name} failed: {output.error}")
