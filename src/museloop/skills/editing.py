"""Editing skill — FFmpeg post-processing + OpenCV analysis."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from museloop.skills.base import BaseSkill, SkillInput, SkillOutput
from museloop.utils.logging import get_logger

logger = get_logger(__name__)

# Allowed file extensions for media inputs
_ALLOWED_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".mp3", ".wav", ".aac", ".flac", ".ogg", ".png", ".jpg"}


def _validate_media_path(path: str, output_dir: str | None = None) -> Path:
    """Validate that a media path is safe (no traversal, valid extension)."""
    # Check for traversal BEFORE resolving (resolve normalizes ".." away)
    raw = Path(path)
    if ".." in raw.parts:
        raise ValueError(f"Path traversal detected: {path}")
    p = raw.resolve()
    if p.suffix.lower() not in _ALLOWED_EXTENSIONS:
        raise ValueError(f"Disallowed file extension: {p.suffix}")
    if output_dir:
        out = Path(output_dir).resolve()
        if not str(p).startswith(str(out)):
            raise ValueError(f"Path outside allowed directory: {path}")
    return p


class EditingSkill(BaseSkill):
    name = "editing"
    description = "Post-processing: trim, concatenate, overlay audio, format conversion via FFmpeg"

    async def execute(self, input: SkillInput, config: dict[str, Any]) -> SkillOutput:
        """Execute an editing operation based on params."""
        output_path = config.get("output_path", "output.mp4")
        operation = input.params.get("operation", "concat")

        if operation == "concat":
            return await self._concat_videos(input, output_path)
        elif operation == "overlay_audio":
            return await self._overlay_audio(input, output_path)
        elif operation == "trim":
            return await self._trim(input, output_path)
        elif operation == "convert":
            return await self._convert(input, output_path)
        else:
            return SkillOutput(success=False, error=f"Unknown operation: {operation}")

    async def _concat_videos(self, input: SkillInput, output_path: str) -> SkillOutput:
        """Concatenate multiple video files."""
        input_files = input.params.get("input_files", [])
        if not input_files:
            return SkillOutput(success=False, error="No input files for concatenation")

        # Validate all input paths
        try:
            validated = [_validate_media_path(f) for f in input_files]
        except ValueError as e:
            return SkillOutput(success=False, error=str(e))

        # Create concat file list
        concat_path = Path(output_path).parent / "concat_list.txt"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(concat_path, "w") as f:
            for file in validated:
                f.write(f"file '{file}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_path),
            "-c", "copy",
            output_path,
        ]

        return await self._run_ffmpeg(cmd, output_path, {"operation": "concat"})

    async def _overlay_audio(self, input: SkillInput, output_path: str) -> SkillOutput:
        """Overlay audio track onto a video."""
        video_path = input.params.get("video_path", "")
        audio_path = input.params.get("audio_path", "")
        if not video_path or not audio_path:
            return SkillOutput(success=False, error="Both video_path and audio_path required")

        try:
            video_path = str(_validate_media_path(video_path))
            audio_path = str(_validate_media_path(audio_path))
        except ValueError as e:
            return SkillOutput(success=False, error=str(e))

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            output_path,
        ]

        return await self._run_ffmpeg(cmd, output_path, {"operation": "overlay_audio"})

    async def _trim(self, input: SkillInput, output_path: str) -> SkillOutput:
        """Trim a video/audio file."""
        input_file = input.params.get("input_file", "")
        start = input.params.get("start", "0")
        duration = input.params.get("duration", "10")

        if not input_file:
            return SkillOutput(success=False, error="input_file required for trim")

        try:
            input_file = str(_validate_media_path(input_file))
        except ValueError as e:
            return SkillOutput(success=False, error=str(e))

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y",
            "-i", input_file,
            "-ss", str(start),
            "-t", str(duration),
            "-c", "copy",
            output_path,
        ]

        return await self._run_ffmpeg(cmd, output_path, {"operation": "trim"})

    async def _convert(self, input: SkillInput, output_path: str) -> SkillOutput:
        """Convert media format."""
        input_file = input.params.get("input_file", "")
        if not input_file:
            return SkillOutput(success=False, error="input_file required for convert")

        try:
            input_file = str(_validate_media_path(input_file))
        except ValueError as e:
            return SkillOutput(success=False, error=str(e))

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y",
            "-i", input_file,
            output_path,
        ]

        return await self._run_ffmpeg(cmd, output_path, {"operation": "convert"})

    async def _run_ffmpeg(
        self, cmd: list[str], output_path: str, metadata: dict[str, Any]
    ) -> SkillOutput:
        """Run an ffmpeg command and return the result."""
        try:
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
                    metadata={"source": "ffmpeg", **metadata},
                )
            else:
                error_msg = stderr.decode()[-200:]
                logger.error("ffmpeg_failed", error=error_msg)
                return SkillOutput(success=False, error=f"ffmpeg error: {error_msg}")
        except FileNotFoundError:
            return SkillOutput(success=False, error="ffmpeg not found — install it via your package manager")
        except Exception as e:
            return SkillOutput(success=False, error=f"ffmpeg execution error: {e}")
