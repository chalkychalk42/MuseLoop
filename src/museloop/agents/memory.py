"""MemoryAgent: manages persistent context across iterations."""

from __future__ import annotations

import json
from typing import Any

from museloop.agents.base import BaseAgent, logger
from museloop.core.state import LoopState


class MemoryAgent(BaseAgent):
    agent_name = "memory"
    prompt_file = "memory_agent.md"

    async def run(self, state: LoopState) -> dict[str, Any]:
        logger.info("memory_agent_start", iteration=state["iteration"])

        memory = state.get("memory", {})
        critique = state.get("critique", {})
        iteration = state["iteration"]

        # First iteration: initialize memory from brief
        if iteration <= 1:
            return {
                "memory": {
                    "themes": [],
                    "successful_approaches": [],
                    "rejected_approaches": [],
                    "iteration_summaries": [],
                },
                "status": "planning",
                "messages": [
                    {
                        "role": "assistant",
                        "content": f"[MemoryAgent] Initialized memory for new project.",
                    }
                ],
            }

        # Subsequent iterations: summarize and update memory
        user_message = f"""
Iteration {iteration}. Update the project memory based on the last iteration's results.

Current memory: {json.dumps(memory)}
Last critique: {json.dumps(critique)}

Respond with JSON:
{{
    "themes": ["key creative themes identified"],
    "successful_approaches": ["what worked well"],
    "rejected_approaches": ["what to avoid"],
    "iteration_summaries": ["one-line summary per iteration"]
}}
"""
        try:
            updated_memory = await self._call_llm_json(user_message)
            return {
                "memory": updated_memory,
                "status": "planning",
                "messages": [
                    {
                        "role": "assistant",
                        "content": f"[MemoryAgent] Updated memory for iteration {iteration}.",
                    }
                ],
            }
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("memory_agent_llm_error", error=str(e))
            return {
                "memory": memory,
                "status": "planning",
                "messages": [
                    {
                        "role": "assistant",
                        "content": f"[MemoryAgent] Kept existing memory (parse error).",
                    }
                ],
            }
