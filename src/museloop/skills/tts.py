"""Text-to-speech skill — Bark/Tortoise local + Replicate fallback."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from museloop.skills.base import BaseSkill, SkillInput, SkillOutput
from museloop.utils.logging import get_logger
from museloop.utils.retry import retry_generation

logger = get_logger(__name__)


class TTSSkill(BaseSkill):
    name = "tts"
    description = "Text-to-speech audio generation via Bark or Replicate"

    def __init__(self, replicate_api_key: str | None = None):
        self.replicate_api_key = replicate_api_key

    async def execute(self, input: SkillInput, config: dict[str, Any]) -> SkillOutput:
        output_path = config.get("output_path", "output.wav")

        # Try local Bark
        try:
            return await self._generate_local(input, output_path)
        except Exception as e:
            logger.warning("tts_local_failed", error=str(e))

        # Try Replicate
        if self.replicate_api_key:
            try:
                return await self._generate_replicate(input, output_path)
            except Exception as e:
                logger.warning("tts_replicate_failed", error=str(e))

        return SkillOutput(success=False, error="No TTS backend available")

    async def _generate_local(self, input: SkillInput, output_path: str) -> SkillOutput:
        """Generate speech via local Bark model."""
        try:
            import numpy as np
            import scipy.io.wavfile
            from bark import SAMPLE_RATE, generate_audio, preload_models
        except ImportError:
            raise RuntimeError("bark not installed — install with: pip install bark")

        preload_models()
        audio_array = generate_audio(
            input.prompt,
            history_prompt=input.params.get("voice_preset", "v2/en_speaker_6"),
        )

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        scipy.io.wavfile.write(output_path, rate=SAMPLE_RATE, data=audio_array)

        return SkillOutput(
            success=True,
            asset_paths=[output_path],
            metadata={"source": "bark_local"},
        )

    @retry_generation
    async def _generate_replicate(self, input: SkillInput, output_path: str) -> SkillOutput:
        """Generate speech via Replicate Bark."""
        import asyncio

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers={"Authorization": f"Bearer {self.replicate_api_key}"},
                json={
                    "version": "suno-ai/bark",
                    "input": {
                        "prompt": input.prompt,
                        "text_temp": input.params.get("temperature", 0.7),
                    },
                },
            )
            response.raise_for_status()
            prediction = response.json()

            for _ in range(120):
                await asyncio.sleep(2)
                status_resp = await client.get(
                    prediction["urls"]["get"],
                    headers={"Authorization": f"Bearer {self.replicate_api_key}"},
                )
                status = status_resp.json()
                if status["status"] == "succeeded":
                    audio_url = status["output"].get("audio_out", status["output"])
                    if isinstance(audio_url, list):
                        audio_url = audio_url[0]
                    audio_resp = await client.get(audio_url)
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(output_path).write_bytes(audio_resp.content)
                    return SkillOutput(
                        success=True,
                        asset_paths=[output_path],
                        metadata={"source": "replicate_bark"},
                    )
                elif status["status"] == "failed":
                    return SkillOutput(success=False, error="TTS failed")

        return SkillOutput(success=False, error="TTS timed out")
