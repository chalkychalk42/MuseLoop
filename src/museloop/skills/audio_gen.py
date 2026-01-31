"""Audio generation skill — AudioCraft/MusicGen + TTS."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import httpx

from museloop.skills.base import BaseSkill, SkillInput, SkillOutput
from museloop.utils.logging import get_logger
from museloop.utils.retry import retry_generation

logger = get_logger(__name__)


class AudioGenSkill(BaseSkill):
    name = "audio_gen"
    description = "Generate audio/music via AudioCraft (MusicGen) or Replicate API"

    def __init__(self, replicate_api_key: str | None = None):
        self.replicate_api_key = replicate_api_key

    async def execute(self, input: SkillInput, config: dict[str, Any]) -> SkillOutput:
        """Generate audio. Tries local MusicGen first, then Replicate."""
        output_path = config.get("output_path", "output.wav")

        # Try local AudioCraft
        try:
            return await self._generate_local(input, output_path)
        except Exception as e:
            logger.warning("local_audio_gen_failed", error=str(e))

        # Fallback to Replicate
        if self.replicate_api_key:
            try:
                return await self._generate_replicate(input, output_path)
            except Exception as e:
                logger.warning("replicate_audio_failed", error=str(e))

        # Generate silence as placeholder
        return await self._generate_placeholder(input, output_path)

    async def _generate_local(self, input: SkillInput, output_path: str) -> SkillOutput:
        """Generate audio using local AudioCraft MusicGen."""
        try:
            import torch
            import torchaudio
            from audiocraft.models import MusicGen

            model = MusicGen.get_pretrained("facebook/musicgen-small")
            model.set_generation_params(
                duration=input.params.get("duration", 10),
                temperature=input.params.get("temperature", 1.0),
            )

            wav = model.generate([input.prompt])

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            torchaudio.save(output_path, wav[0].cpu(), sample_rate=32000)

            return SkillOutput(
                success=True,
                asset_paths=[output_path],
                metadata={"source": "local_musicgen", "duration": input.params.get("duration", 10)},
            )
        except ImportError:
            raise RuntimeError("audiocraft/torch not installed — install with [gpu] extra")

    @retry_generation
    async def _generate_replicate(self, input: SkillInput, output_path: str) -> SkillOutput:
        """Generate audio via Replicate API (MusicGen)."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers={"Authorization": f"Bearer {self.replicate_api_key}"},
                json={
                    "version": "671ac645ce5e552cc63a54a2bbff63fcf798043ac68f86b6588bd76095c297bf",
                    "input": {
                        "prompt": input.prompt,
                        "duration": input.params.get("duration", 10),
                        "model_version": "stereo-melody-large",
                    },
                },
            )
            response.raise_for_status()
            prediction = response.json()

            for _ in range(120):
                await asyncio.sleep(2)
                status_response = await client.get(
                    prediction["urls"]["get"],
                    headers={"Authorization": f"Bearer {self.replicate_api_key}"},
                )
                status = status_response.json()
                if status["status"] == "succeeded":
                    audio_url = status["output"]
                    if isinstance(audio_url, list):
                        audio_url = audio_url[0]
                    audio_response = await client.get(audio_url)
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(output_path).write_bytes(audio_response.content)
                    return SkillOutput(
                        success=True,
                        asset_paths=[output_path],
                        metadata={"source": "replicate"},
                    )
                elif status["status"] == "failed":
                    return SkillOutput(success=False, error=status.get("error", "Failed"))

        return SkillOutput(success=False, error="Replicate audio generation timed out")

    async def _generate_placeholder(self, input: SkillInput, output_path: str) -> SkillOutput:
        """Generate a silent audio file as placeholder."""
        try:
            duration = input.params.get("duration", 10)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"anullsrc=r=44100:cl=stereo",
                "-t", str(duration),
                "-c:a", "pcm_s16le",
                output_path,
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode == 0:
                return SkillOutput(
                    success=True,
                    asset_paths=[output_path],
                    metadata={"source": "placeholder", "duration": duration},
                )
            else:
                return SkillOutput(success=False, error=f"ffmpeg failed: {stderr.decode()[:200]}")
        except Exception as e:
            return SkillOutput(success=False, error=f"Placeholder audio failed: {e}")
