"""CriticAgent: evaluates generated assets and provides quality scores."""

from __future__ import annotations

import json
from typing import Any

from museloop.agents.base import BaseAgent, logger
from museloop.core.state import LoopState
from museloop.llm.base import LLMBackend


class CriticAgent(BaseAgent):
    agent_name = "critic"
    prompt_file = "critic_agent.md"

    def __init__(self, llm: LLMBackend, prompts_dir: str, quality_threshold: float = 0.7):
        super().__init__(llm, prompts_dir)
        self.quality_threshold = quality_threshold

    async def run(self, state: LoopState) -> dict[str, Any]:
        logger.info("critic_agent_start", iteration=state["iteration"])

        brief = state["brief"]
        assets = state.get("assets", [])
        plan = state.get("plan", [])
        iteration = state["iteration"]

        if not assets:
            return {
                "critique": {
                    "score": 0.0,
                    "pass": False,
                    "feedback": "No assets were generated.",
                    "strengths": [],
                    "improvements": ["Generate at least the required assets"],
                    "priority_fixes": ["Ensure skills are available and configured"],
                },
                "messages": [
                    {
                        "role": "assistant",
                        "content": "[CriticAgent] Score: 0.0 — no assets generated.",
                    }
                ],
            }

        # Build asset summary for the critic
        asset_summary = []
        for asset in assets:
            asset_summary.append({
                "type": asset.get("type"),
                "path": asset.get("path"),
                "step": asset.get("step"),
                "metadata": asset.get("metadata", {}),
            })

        user_message = f"""
Evaluate these generated assets against the original brief.

Brief: {json.dumps(brief)}
Plan ({len(plan)} tasks): {json.dumps(plan[:10])}
Generated assets ({len(assets)}): {json.dumps(asset_summary)}
Iteration: {iteration}
Quality threshold: {self.quality_threshold}

Score from 0.0 to 1.0 and provide detailed feedback.
Set "pass" to true if score >= {self.quality_threshold}.
"""

        try:
            result = await self._call_llm_json(user_message)
            score = float(result.get("score", 0.0))
            result["score"] = score
            result["pass"] = score >= self.quality_threshold

            logger.info(
                "critic_evaluation",
                score=score,
                passed=result["pass"],
                iteration=iteration,
            )

            return {
                "critique": result,
                "messages": [
                    {
                        "role": "assistant",
                        "content": (
                            f"[CriticAgent] Score: {score:.2f} "
                            f"({'PASS' if result['pass'] else 'REVISE'}). "
                            f"Feedback: {result.get('feedback', '')[:200]}"
                        ),
                    }
                ],
            }
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error("critic_agent_error", error=str(e))
            return {
                "critique": {
                    "score": 0.5,
                    "pass": False,
                    "feedback": f"Evaluation error: {e}. Defaulting to revision.",
                    "strengths": [],
                    "improvements": ["Fix evaluation pipeline"],
                    "priority_fixes": [],
                },
                "messages": [
                    {
                        "role": "assistant",
                        "content": f"[CriticAgent] Evaluation error, defaulting to revision.",
                    }
                ],
            }
