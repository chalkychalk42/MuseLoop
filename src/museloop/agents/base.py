"""Base agent class — all agents inherit from this."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from museloop.core.state import LoopState
from museloop.llm.base import LLMBackend
from museloop.utils.logging import get_logger

logger = get_logger(__name__)

# Regex to extract JSON from markdown fences or raw text
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)


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
        """Call the LLM and parse the response as JSON.

        Handles markdown code fences, leading/trailing text around JSON,
        and provides clear error messages on parse failure.
        """
        response = await self._call_llm(user_message, **kwargs)
        return self._parse_json_response(response)

    @staticmethod
    def _parse_json_response(response: str) -> dict[str, Any]:
        """Extract and parse JSON from an LLM response string."""
        text = response.strip()

        # Try 1: direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try 2: extract from markdown code fence
        match = _JSON_BLOCK_RE.search(text)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try 3: find first { ... } block in the text
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            try:
                return json.loads(text[brace_start : brace_end + 1])
            except json.JSONDecodeError:
                pass

        raise json.JSONDecodeError(
            f"Could not extract valid JSON from LLM response ({len(text)} chars)",
            text[:200],
            0,
        )

    @abstractmethod
    async def run(self, state: LoopState) -> dict[str, Any]:
        """Execute this agent's logic. Returns a dict of state updates."""
        ...
