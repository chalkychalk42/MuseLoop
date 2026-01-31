"""LLM backend protocol — abstraction layer for swapping providers."""

from __future__ import annotations

from typing import AsyncIterator, Protocol, runtime_checkable


@runtime_checkable
class LLMBackend(Protocol):
    """Protocol for LLM backends. Implement this to add a new provider."""

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Single-shot completion. Returns the full response text."""
        ...

    async def stream(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Streaming completion. Yields text chunks."""
        ...
