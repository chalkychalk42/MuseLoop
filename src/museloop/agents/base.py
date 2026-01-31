"""Base agent class — all agents inherit from this."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from museloop.core.state import LoopState
from museloop.llm.base import LLMBackend
from museloop.utils.logging import get_logger

logger = get_logger(__name__)


class BaseAgent(ABC):
    """Base class for all MuseLoop agents.

    Provides LLM access, prompt loading, and a standard interface.
    """

    agent_name: str = "base"
    prompt_file: str = "base_agent.md"

    def __init__(self, llm: LLMBackend, prompts_dir: str | Path = "./prompts"):
        self.llm = llm
        self.system_prompt = self._load_prompt(prompts_dir)

    def _load_prompt(self, prompts_dir: str | Path) -> str:
        """Load this agent's system prompt from the prompts directory."""
        path = Path(prompts_dir) / self.prompt_file
        if path.exists():
            return path.read_text()
        logger.warning("prompt_not_found", agent=self.agent_name, path=str(path))
        return f"You are the {self.agent_name} agent."

    async def _call_llm(self, user_message: str, **kwargs: Any) -> str:
        """Call the LLM and return the response text."""
        return await self.llm.generate(
            system_prompt=self.system_prompt,
            user_message=user_message,
            **kwargs,
        )

    async def _call_llm_json(self, user_message: str, **kwargs: Any) -> dict[str, Any]:
        """Call the LLM and parse the response as JSON."""
        response = await self._call_llm(user_message, **kwargs)
        # Strip markdown code fences if present
        text = response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last lines (```json and ```)
            lines = [l for l in lines[1:] if not l.strip() == "```"]
            text = "\n".join(lines)
        return json.loads(text)

    @abstractmethod
    async def run(self, state: LoopState) -> dict[str, Any]:
        """Execute this agent's logic. Returns a dict of state updates."""
        ...
