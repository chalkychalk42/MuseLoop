"""ResearchAgent: gathers context and reference material (stub — expand with web search later)."""

from __future__ import annotations

import json
from typing import Any

from museloop.agents.base import BaseAgent, logger
from museloop.core.state import LoopState


class ResearchAgent(BaseAgent):
    agent_name = "research"
    prompt_file = "research_agent.md"

    async def run(self, state: LoopState) -> dict[str, Any]:
        logger.info("research_agent_start", iteration=state["iteration"])

        brief = state["brief"]
        memory = state.get("memory", {})

        user_message = f"""
Analyze this creative brief and provide research context to help the other agents.

Brief: {json.dumps(brief)}
Existing memory: {json.dumps(memory)}

Provide style keywords, prompt engineering tips, and recommendations.
"""

        try:
            result = await self._call_llm_json(user_message)
            # Merge research into memory
            updated_memory = {**memory}
            if "style_keywords" in result:
                updated_memory["style_keywords"] = result["style_keywords"]
            if "negative_prompts" in result:
                updated_memory["negative_prompts"] = result["negative_prompts"]
            if "recommendations" in result:
                updated_memory["recommendations"] = result["recommendations"]

            return {
                "memory": updated_memory,
                "messages": [
                    {
                        "role": "assistant",
                        "content": (
                            f"[ResearchAgent] Added context: "
                            f"{len(result.get('style_keywords', []))} style keywords, "
                            f"{len(result.get('recommendations', []))} recommendations."
                        ),
                    }
                ],
            }
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("research_agent_error", error=str(e))
            return {
                "memory": memory,
                "messages": [
                    {
                        "role": "assistant",
                        "content": f"[ResearchAgent] Skipped research (error: {e}).",
                    }
                ],
            }
