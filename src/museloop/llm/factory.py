"""Factory for creating LLM backend instances."""

from __future__ import annotations

from museloop.config import MuseLoopConfig
from museloop.llm.base import LLMBackend
from museloop.llm.claude import ClaudeBackend
from museloop.llm.openai_compat import OpenAICompatBackend


def get_llm_backend(config: MuseLoopConfig) -> LLMBackend:
    """Create an LLM backend instance based on configuration."""
    if config.llm_backend == "claude":
        if not config.anthropic_api_key:
            raise ValueError(
                "MUSELOOP_ANTHROPIC_API_KEY is required when using the Claude backend. "
                "Set it in your .env file or environment."
            )
        return ClaudeBackend(
            api_key=config.anthropic_api_key,
            model=config.claude_model,
        )
    elif config.llm_backend == "openai":
        return OpenAICompatBackend(
            api_key=config.openai_api_key or "not-needed",
            base_url=config.openai_base_url or "http://localhost:11434/v1",
        )
    else:
        raise ValueError(f"Unknown LLM backend: {config.llm_backend!r}. Use 'claude' or 'openai'.")
