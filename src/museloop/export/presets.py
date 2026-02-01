"""Export presets for common platforms."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExportPreset:
    """Defines output format for a specific platform."""

    name: str
    width: int
    height: int
    aspect_ratio: str
    fps: int = 30
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    video_bitrate: str = "8M"
    audio_bitrate: str = "192k"
    pixel_format: str = "yuv420p"
    max_file_size_mb: int | None = None


PRESETS: dict[str, ExportPreset] = {
    "youtube_1080p": ExportPreset(
        name="youtube_1080p",
        width=1920,
        height=1080,
        aspect_ratio="16:9",
        fps=30,
        video_bitrate="8M",
    ),
    "youtube_4k": ExportPreset(
        name="youtube_4k",
        width=3840,
        height=2160,
        aspect_ratio="16:9",
        fps=30,
        video_bitrate="35M",
    ),
    "instagram_reels": ExportPreset(
        name="instagram_reels",
        width=1080,
        height=1920,
        aspect_ratio="9:16",
        fps=30,
        video_bitrate="5M",
        max_file_size_mb=250,
    ),
    "instagram_square": ExportPreset(
        name="instagram_square",
        width=1080,
        height=1080,
        aspect_ratio="1:1",
        fps=30,
        video_bitrate="5M",
    ),
    "tiktok": ExportPreset(
        name="tiktok",
        width=1080,
        height=1920,
        aspect_ratio="9:16",
        fps=30,
        video_bitrate="4M",
        max_file_size_mb=287,
    ),
    "twitter": ExportPreset(
        name="twitter",
        width=1280,
        height=720,
        aspect_ratio="16:9",
        fps=30,
        video_bitrate="5M",
        max_file_size_mb=512,
    ),
    # --- Crypto / Memecoin presets ---
    "dexscreener_banner": ExportPreset(
        name="dexscreener_banner",
        width=1500,
        height=500,
        aspect_ratio="3:1",
        video_bitrate="4M",
    ),
    "dexscreener_icon": ExportPreset(
        name="dexscreener_icon",
        width=256,
        height=256,
        aspect_ratio="1:1",
        video_bitrate="2M",
    ),
    "pumpfun_banner": ExportPreset(
        name="pumpfun_banner",
        width=800,
        height=200,
        aspect_ratio="4:1",
        video_bitrate="3M",
    ),
    "pumpfun_icon": ExportPreset(
        name="pumpfun_icon",
        width=400,
        height=400,
        aspect_ratio="1:1",
        video_bitrate="2M",
    ),
    "twitter_header": ExportPreset(
        name="twitter_header",
        width=1500,
        height=500,
        aspect_ratio="3:1",
        video_bitrate="4M",
    ),
    "twitter_post": ExportPreset(
        name="twitter_post",
        width=1200,
        height=675,
        aspect_ratio="16:9",
        video_bitrate="4M",
    ),
    "twitter_profile": ExportPreset(
        name="twitter_profile",
        width=400,
        height=400,
        aspect_ratio="1:1",
        video_bitrate="2M",
    ),
    "telegram_sticker": ExportPreset(
        name="telegram_sticker",
        width=512,
        height=512,
        aspect_ratio="1:1",
        video_bitrate="2M",
    ),
    "discord_banner": ExportPreset(
        name="discord_banner",
        width=960,
        height=540,
        aspect_ratio="16:9",
        video_bitrate="4M",
    ),
    "token_logo_sm": ExportPreset(
        name="token_logo_sm",
        width=128,
        height=128,
        aspect_ratio="1:1",
        video_bitrate="1M",
    ),
    "token_logo_lg": ExportPreset(
        name="token_logo_lg",
        width=1024,
        height=1024,
        aspect_ratio="1:1",
        video_bitrate="4M",
    ),
}


def get_preset(name: str) -> ExportPreset:
    """Get an export preset by name."""
    if name not in PRESETS:
        available = ", ".join(PRESETS.keys())
        raise KeyError(f"Preset '{name}' not found. Available: {available}")
    return PRESETS[name]


def list_presets() -> list[dict[str, str]]:
    """List all presets with basic info."""
    return [
        {
            "name": p.name,
            "resolution": f"{p.width}x{p.height}",
            "aspect_ratio": p.aspect_ratio,
        }
        for p in PRESETS.values()
    ]
