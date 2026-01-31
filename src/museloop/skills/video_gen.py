"""Video generation skill — local model inference + Replicate fallback."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any

import httpx

from museloop.skills.base import BaseSkill, SkillInput, SkillOutput
from museloop.utils.logging import get_logger
from museloop.utils.retry import retry_generation

logger = get_logger(__name__)


def _sanitize_drawtext(text: str) -> str:
    """Escape text for safe use in ffmpeg drawtext filter."""
    # Remove characters that have special meaning in ffmpeg filters
    text = re.sub(r"[':;\\]", "", text)
    # Limit length to prevent abuse
    return text[:80]


class VideoGenSkill(BaseSkill):
    name = "video_gen"
    description = "Generate videos via local models (Wan2.2/CogVideo) or Replicate API"

    def __init__(self, replicate_api_key: str | None = None):
        self.replicate_api_key = replicate_api_key

    async def execute(self, input: SkillInput, config: dict[str, Any]) -> SkillOutput:
        """Generate a video clip."""
        output_path = config.get("output_path", "output.mp4")

        # Try local diffusers-based generation
        try:
            return await self._generate_local(input, output_path)
        except Exception as e:
            logger.warning("local_video_gen_failed", error=str(e))

        # Fallback to Replicate
        if self.replicate_api_key:
            try:
                return await self._generate_replicate(input, output_path)
            except Exception as e:
                logger.warning("replicate_video_failed", error=str(e))

        # Last resort: generate a slideshow from placeholder images
        return await self._generate_placeholder(input, output_path)

    async def _generate_local(self, input: SkillInput, output_path: str) -> SkillOutput:
        """Generate video using local diffusers models (Wan2.2 or CogVideoX)."""
        try:
            import torch
            from diffusers import DiffusionPipeline

            pipe = DiffusionPipeline.from_pretrained(
                "THUDM/CogVideoX-2b",
                torch_dtype=torch.float16,
            )
            pipe.to("cuda" if torch.cuda.is_available() else "cpu")

            video = pipe(
                prompt=input.prompt,
                num_frames=input.params.get("num_frames", 48),
                guidance_scale=input.params.get("guidance_scale", 6.0),
            ).frames[0]

            # Export frames to video via ffmpeg
            from diffusers.utils import export_to_video

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            export_to_video(video, output_path, fps=input.params.get("fps", 8))

            return SkillOutput(
                success=True,
                asset_paths=[output_path],
                metadata={"source": "local_diffusers", "frames": len(video)},
            )
        except ImportError:
            raise RuntimeError("torch/diffusers not installed — install with [gpu] extra")

    @retry_generation
    async def _generate_replicate(self, input: SkillInput, output_path: str) -> SkillOutput:
        """Generate video via Replicate API."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers={"Authorization": f"Bearer {self.replicate_api_key}"},
                json={
                    "version": "9f747673945c62801b13b84701c783929c0ee784e4144e26f09a2e63601db921",
                    "input": {
                        "prompt": input.prompt,
                        "num_frames": input.params.get("num_frames", 48),
                    },
                },
            )
            response.raise_for_status()
            prediction = response.json()

            for _ in range(180):  # 6 minute timeout for video
                await asyncio.sleep(2)
                status_response = await client.get(
                    prediction["urls"]["get"],
                    headers={"Authorization": f"Bearer {self.replicate_api_key}"},
                )
                status = status_response.json()
                if status["status"] == "succeeded":
                    video_url = status["output"]
                    if isinstance(video_url, list):
                        video_url = video_url[0]
                    vid_response = await client.get(video_url)
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(output_path).write_bytes(vid_response.content)
                    return SkillOutput(
                        success=True,
                        asset_paths=[output_path],
                        metadata={"source": "replicate"},
                    )
                elif status["status"] == "failed":
                    return SkillOutput(success=False, error=status.get("error", "Failed"))

        return SkillOutput(success=False, error="Replicate video generation timed out")

    async def _generate_placeholder(self, input: SkillInput, output_path: str) -> SkillOutput:
        """Generate a placeholder video (color bars + text) via ffmpeg."""
        try:
            duration = input.params.get("duration", 5)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            safe_text = _sanitize_drawtext(input.prompt)
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"color=c=0x1e1e28:s=1280x720:d={duration}",
                "-vf", f"drawtext=text='[MuseLoop Placeholder]\\n{safe_text}'"
                       ":fontcolor=white:fontsize=24:x=(w-tw)/2:y=(h-th)/2",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
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
            return SkillOutput(success=False, error=f"Placeholder video failed: {e}")
