"""Export renderer — ffmpeg-based resize, crop, letterbox, and encode."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from museloop.export.presets import ExportPreset, get_preset
from museloop.utils.logging import get_logger

logger = get_logger(__name__)


class ExportRenderer:
    """Renders output files to match export presets using ffmpeg."""

    def __init__(self, preset: ExportPreset | str) -> None:
        if isinstance(preset, str):
            preset = get_preset(preset)
        self.preset = preset

    def render(
        self,
        input_path: str,
        output_path: str | None = None,
        mode: str = "fit",
    ) -> str:
        """Render input file to the preset format.

        Args:
            input_path: Path to the source video/image.
            output_path: Destination path. Auto-generated if None.
            mode: Resize strategy — "fit" (letterbox), "fill" (crop), "stretch".

        Returns:
            Path to the rendered output file.
        """
        src = Path(input_path)
        if not src.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if output_path is None:
            output_path = str(
                src.parent / f"{src.stem}_{self.preset.name}{src.suffix}"
            )

        p = self.preset
        vf = self._build_video_filter(mode)

        cmd = [
            "ffmpeg", "-y",
            "-i", str(src),
            "-vf", vf,
            "-c:v", p.video_codec,
            "-b:v", p.video_bitrate,
            "-c:a", p.audio_codec,
            "-b:a", p.audio_bitrate,
            "-pix_fmt", p.pixel_format,
            "-r", str(p.fps),
            "-movflags", "+faststart",
            output_path,
        ]

        logger.info(
            "export_render_start",
            input=input_path,
            output=output_path,
            preset=p.name,
            mode=mode,
        )

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("export_render_failed", stderr=result.stderr[:500])
            raise RuntimeError(f"ffmpeg export failed: {result.stderr[:200]}")

        logger.info("export_render_complete", output=output_path)
        return output_path

    def render_image(
        self,
        input_path: str,
        output_path: str | None = None,
        mode: str = "fit",
    ) -> str:
        """Render a single image to the preset dimensions.

        Args:
            input_path: Path to the source image.
            output_path: Destination path. Auto-generated if None.
            mode: Resize strategy.

        Returns:
            Path to the rendered image.
        """
        src = Path(input_path)
        if not src.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if output_path is None:
            output_path = str(src.parent / f"{src.stem}_{self.preset.name}.png")

        p = self.preset
        vf = self._build_video_filter(mode)

        cmd = [
            "ffmpeg", "-y",
            "-i", str(src),
            "-vf", vf,
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg image export failed: {result.stderr[:200]}")

        return output_path

    def _build_video_filter(self, mode: str) -> str:
        """Build the ffmpeg video filter string for the given mode."""
        p = self.preset

        if mode == "fill":
            # Crop to aspect ratio then scale
            return (
                f"scale={p.width}:{p.height}:force_original_aspect_ratio=increase,"
                f"crop={p.width}:{p.height}"
            )
        elif mode == "stretch":
            # Direct scale (may distort)
            return f"scale={p.width}:{p.height}"
        else:
            # "fit" — scale to fit with letterbox/pillarbox
            return (
                f"scale={p.width}:{p.height}:force_original_aspect_ratio=decrease,"
                f"pad={p.width}:{p.height}:(ow-iw)/2:(oh-ih)/2:color=black"
            )

    def get_info(self) -> dict[str, Any]:
        """Return preset info as a dict."""
        p = self.preset
        return {
            "name": p.name,
            "resolution": f"{p.width}x{p.height}",
            "aspect_ratio": p.aspect_ratio,
            "fps": p.fps,
            "video_codec": p.video_codec,
            "video_bitrate": p.video_bitrate,
        }
