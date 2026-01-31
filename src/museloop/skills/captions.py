"""Captions/subtitles skill — Whisper transcription + ffmpeg burn-in."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from museloop.skills.base import BaseSkill, SkillInput, SkillOutput
from museloop.utils.logging import get_logger

logger = get_logger(__name__)


class CaptionsSkill(BaseSkill):
    name = "captions"
    description = "Generate captions/subtitles from audio/video via Whisper"

    def __init__(self, replicate_api_key: str | None = None):
        self.replicate_api_key = replicate_api_key

    async def execute(self, input: SkillInput, config: dict[str, Any]) -> SkillOutput:
        output_path = config.get("output_path", "output.srt")
        source_media = input.params.get("source_media", "")

        if not source_media or not Path(source_media).exists():
            return SkillOutput(success=False, error="source_media parameter required")

        # Try local Whisper
        try:
            return await self._transcribe_local(source_media, output_path, input)
        except Exception as e:
            logger.warning("whisper_local_failed", error=str(e))

        # Try Replicate Whisper
        if self.replicate_api_key:
            try:
                return await self._transcribe_replicate(source_media, output_path)
            except Exception as e:
                logger.warning("whisper_replicate_failed", error=str(e))

        return SkillOutput(success=False, error="No transcription backend available")

    async def _transcribe_local(
        self, source_media: str, output_path: str, input: SkillInput
    ) -> SkillOutput:
        """Transcribe with local Whisper model."""
        try:
            import whisper
        except ImportError:
            raise RuntimeError("openai-whisper not installed — pip install openai-whisper")

        model_size = input.params.get("model_size", "base")
        model = whisper.load_model(model_size)
        result = model.transcribe(source_media)

        # Write SRT format
        srt_content = self._to_srt(result["segments"])
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(srt_content, encoding="utf-8")

        # Optionally burn captions into video
        burn_in = input.params.get("burn_in", False)
        if burn_in and source_media.endswith((".mp4", ".mov", ".mkv")):
            burned_path = output_path.replace(".srt", "_captioned.mp4")
            self._burn_captions(source_media, output_path, burned_path)
            return SkillOutput(
                success=True,
                asset_paths=[output_path, burned_path],
                metadata={"source": "whisper_local", "segments": len(result["segments"])},
            )

        return SkillOutput(
            success=True,
            asset_paths=[output_path],
            metadata={"source": "whisper_local", "segments": len(result["segments"])},
        )

    async def _transcribe_replicate(self, source_media: str, output_path: str) -> SkillOutput:
        """Transcribe with Replicate Whisper."""
        import asyncio
        import base64

        import httpx

        audio_data = base64.b64encode(Path(source_media).read_bytes()).decode()
        data_uri = f"data:audio/wav;base64,{audio_data}"

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers={"Authorization": f"Bearer {self.replicate_api_key}"},
                json={
                    "version": "openai/whisper",
                    "input": {
                        "audio": data_uri,
                        "model": "base",
                        "translate": False,
                    },
                },
            )
            response.raise_for_status()
            prediction = response.json()

            for _ in range(300):
                await asyncio.sleep(2)
                status_resp = await client.get(
                    prediction["urls"]["get"],
                    headers={"Authorization": f"Bearer {self.replicate_api_key}"},
                )
                status = status_resp.json()
                if status["status"] == "succeeded":
                    segments = status["output"].get("segments", [])
                    srt = self._to_srt(segments)
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(output_path).write_text(srt, encoding="utf-8")
                    return SkillOutput(
                        success=True,
                        asset_paths=[output_path],
                        metadata={"source": "replicate_whisper", "segments": len(segments)},
                    )
                elif status["status"] == "failed":
                    return SkillOutput(success=False, error="Whisper transcription failed")

        return SkillOutput(success=False, error="Whisper transcription timed out")

    @staticmethod
    def _to_srt(segments: list[dict[str, Any]]) -> str:
        """Convert Whisper segments to SRT format."""
        lines = []
        for i, seg in enumerate(segments, 1):
            start = seg.get("start", 0.0)
            end = seg.get("end", 0.0)
            text = seg.get("text", "").strip()
            lines.append(str(i))
            lines.append(f"{_format_timestamp(start)} --> {_format_timestamp(end)}")
            lines.append(text)
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _burn_captions(video_path: str, srt_path: str, output_path: str) -> None:
        """Burn SRT subtitles into a video using ffmpeg."""
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", video_path,
                "-vf", f"subtitles={srt_path}",
                "-c:a", "copy",
                output_path,
            ],
            capture_output=True,
            check=True,
        )


def _format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format HH:MM:SS,mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
