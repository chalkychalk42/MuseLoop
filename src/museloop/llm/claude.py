"""Anthropic Claude LLM backend."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, AsyncIterator

import anthropic


# Image extensions supported by Claude's vision API
_VISION_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


class ClaudeBackend:
    """Anthropic Claude implementation of LLMBackend."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        if not response.content:
            raise ValueError("Claude returned an empty response")
        # Extract text from the first text block, skipping tool_use blocks
        for block in response.content:
            if block.type == "text":
                return block.text
        raise ValueError(f"Claude response contained no text blocks: {[b.type for b in response.content]}")

    async def stream(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        async with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def generate_with_images(
        self,
        system_prompt: str,
        user_message: str,
        image_paths: list[str],
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Send images alongside text to Claude's vision API."""
        content_blocks: list[dict[str, Any]] = []

        for img_path in image_paths:
            p = Path(img_path)
            if not p.exists() or p.suffix.lower() not in _VISION_EXTENSIONS:
                continue
            data = base64.standard_b64encode(p.read_bytes()).decode("utf-8")
            content_blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": _MEDIA_TYPES[p.suffix.lower()],
                    "data": data,
                },
            })

        # Always append the text prompt after images
        content_blocks.append({"type": "text", "text": user_message})

        # If no valid images were found, fall back to text-only
        if len(content_blocks) == 1:
            return await self.generate(
                system_prompt, user_message,
                max_tokens=max_tokens, temperature=temperature,
            )

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": content_blocks}],
        )
        if not response.content:
            raise ValueError("Claude returned an empty response")
        for block in response.content:
            if block.type == "text":
                return block.text
        raise ValueError(
            f"Claude vision response contained no text blocks: {[b.type for b in response.content]}"
        )
