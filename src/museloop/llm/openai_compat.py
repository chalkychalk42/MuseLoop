"""OpenAI-compatible LLM backend (for Ollama, local models, etc.)."""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator

import httpx

logger = logging.getLogger(__name__)


class OpenAICompatBackend:
    """OpenAI-compatible backend. Works with Ollama, vLLM, LM Studio, etc."""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "http://localhost:11434/v1",
        model: str = "llama3.2",
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": False,
                },
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()
            try:
                return data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as e:
                raise ValueError(f"Unexpected response structure from OpenAI-compatible API: {e}")

    async def stream(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": True,
                },
                timeout=120.0,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.startswith("data: ") or line == "data: [DONE]":
                        continue
                    try:
                        chunk = json.loads(line[6:])
                        delta = chunk["choices"][0].get("delta", {})
                        if content := delta.get("content"):
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

    async def generate_with_images(
        self,
        system_prompt: str,
        user_message: str,
        image_paths: list[str],
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Vision not supported — falls back to text-only generate()."""
        logger.warning("OpenAI-compat backend does not support vision; falling back to text-only")
        return await self.generate(
            system_prompt, user_message,
            max_tokens=max_tokens, temperature=temperature,
        )
