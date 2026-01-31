"""ScriptAgent: generates creative text and breaks the brief into an executable plan."""

from __future__ import annotations

import json
from typing import Any

from museloop.agents.base import BaseAgent, logger
from museloop.core.state import LoopState


class ScriptAgent(BaseAgent):
    agent_name = "script"
    prompt_file = "script_agent.md"

    async def run(self, state: LoopState) -> dict[str, Any]:
        logger.info("script_agent_start", iteration=state["iteration"])

        brief = state["brief"]
        memory = state.get("memory", {})
        critique = state.get("critique", {})
        iteration = state["iteration"]

        revision_context = ""
        if iteration > 1 and critique:
            revision_context = f"""
This is revision iteration {iteration}. The critic provided this feedback:
Score: {critique.get('score', 'N/A')}
Feedback: {critique.get('feedback', 'No feedback')}
Priority fixes: {json.dumps(critique.get('priority_fixes', []))}

Incorporate this feedback into your revised plan and script.
"""

        user_message = f"""
Creative Brief: {json.dumps(brief)}
Iteration: {iteration}
Memory context: {json.dumps(memory)}
{revision_context}

Generate a detailed creative plan and script for this brief. Break it into
executable tasks, each mapped to a skill (image_gen, video_gen, audio_gen, editing).
Include detailed prompts for each generation step.
"""

        try:
            result = await self._call_llm_json(user_message)
            plan = result.get("plan", [])
            script = result.get("script", "")

            return {
                "plan": plan,
                "status": "generating",
                "messages": [
                    {
                        "role": "assistant",
                        "content": (
                            f"[ScriptAgent] Created plan with {len(plan)} tasks. "
                            f"Script: {script[:200]}..."
                        ),
                    }
                ],
            }
        except (json.JSONDecodeError, Exception) as e:
            logger.error("script_agent_error", error=str(e))
            # Return a minimal fallback plan
            return {
                "plan": [
                    {
                        "step": 1,
                        "task": brief.get("task", "Generate content"),
                        "skill": "image_gen",
                        "params": {"prompt": brief.get("task", "")},
                    }
                ],
                "status": "generating",
                "messages": [
                    {
                        "role": "assistant",
                        "content": f"[ScriptAgent] Fallback plan created (error: {e}).",
                    }
                ],
            }
