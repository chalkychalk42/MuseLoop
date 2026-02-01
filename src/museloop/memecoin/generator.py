"""Memecoin content generator — produces full asset kits from token metadata."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TokenMeta:
    """Token metadata for content generation."""

    name: str
    ticker: str
    concept: str = ""
    vibe: str = "degen"
    colors: list[str] = field(default_factory=lambda: ["#00ff88", "#ff00ff", "#000000"])
    tagline: str = ""
    website: str = ""
    twitter: str = ""
    chain: str = "SOL"


# Asset specifications for a complete memecoin launch kit
ASSET_SPECS: dict[str, dict[str, Any]] = {
    "token_logo": {
        "skill": "flux_gen",
        "preset": "token_logo_lg",
        "prompt_template": (
            "Design a bold, iconic memecoin logo for ${ticker} — ${concept}. "
            "Clean vector style, centered mascot/symbol, ${vibe} energy, "
            "vibrant colors on transparent-ready dark background. "
            "Crypto token logo, circular composition, bold and memorable. "
            "Colors: ${colors}."
        ),
        "params": {"width": 1024, "height": 1024, "guidance": 4.0},
    },
    "dexscreener_banner": {
        "skill": "flux_gen",
        "preset": "dexscreener_banner",
        "prompt_template": (
            "Wide cinematic banner for ${name} ($${ticker}) cryptocurrency. "
            "${concept}. ${vibe} aesthetic, bold typography showing '$${ticker}', "
            "high energy, trending crypto vibes, neon accents. "
            "Panoramic 3:1 aspect ratio, dark background with ${colors} glow effects. "
            "${tagline}"
        ),
        "params": {"width": 1500, "height": 500, "guidance": 3.5},
    },
    "pumpfun_banner": {
        "skill": "flux_gen",
        "preset": "pumpfun_banner",
        "prompt_template": (
            "Ultra-wide banner for ${name} ($${ticker}) memecoin on pump.fun. "
            "${concept}. Meme energy, ${vibe} style, bold and eye-catching, "
            "4:1 ultra-wide aspect ratio, dark background. ${tagline}"
        ),
        "params": {"width": 800, "height": 200, "guidance": 3.5},
    },
    "twitter_header": {
        "skill": "flux_gen",
        "preset": "twitter_header",
        "prompt_template": (
            "Twitter/X header banner for ${name} ($${ticker}) crypto project. "
            "${concept}. ${vibe} aesthetic, featuring token mascot/logo, "
            "3:1 wide banner, dark theme with ${colors} accents. "
            "Professional yet degen, crypto twitter energy. ${tagline}"
        ),
        "params": {"width": 1500, "height": 500, "guidance": 3.5},
    },
    "twitter_profile": {
        "skill": "flux_gen",
        "preset": "twitter_profile",
        "prompt_template": (
            "Twitter/X profile picture for ${name} ($${ticker}). "
            "${concept}. Clean circular-crop-ready design, bold mascot/icon, "
            "${vibe} style, ${colors} palette, instantly recognizable at small sizes. "
            "Crypto profile pic, memecoin avatar."
        ),
        "params": {"width": 400, "height": 400, "guidance": 4.0},
    },
    "twitter_post_announcement": {
        "skill": "flux_gen",
        "preset": "twitter_post",
        "prompt_template": (
            "Eye-catching Twitter/X announcement image for ${name} ($${ticker}) launch. "
            "${concept}. Bold text 'NOW LIVE' or 'JUST LAUNCHED', "
            "${vibe} energy, rocket/moon imagery, ${colors} color scheme, "
            "crypto launch announcement graphic. ${tagline}"
        ),
        "params": {"width": 1200, "height": 675, "guidance": 3.5},
    },
    "twitter_post_meme": {
        "skill": "flux_gen",
        "preset": "twitter_post",
        "prompt_template": (
            "Viral meme image featuring ${name} ($${ticker}) mascot/concept. "
            "${concept}. Funny, shareable, ${vibe} humor, crypto culture references, "
            "green candle energy, diamond hands vibes. "
            "Meme format, high engagement potential. ${colors} theme."
        ),
        "params": {"width": 1200, "height": 675, "guidance": 3.0},
    },
    "telegram_sticker": {
        "skill": "flux_gen",
        "preset": "telegram_sticker",
        "prompt_template": (
            "Telegram sticker of ${name} ($${ticker}) mascot/character. "
            "${concept}. Expressive, cute, ${vibe} energy, transparent-ready, "
            "sticker art style, bold outlines, vibrant. "
            "Showing excitement/celebration pose. ${colors} palette."
        ),
        "params": {"width": 512, "height": 512, "guidance": 4.0},
    },
    "discord_banner": {
        "skill": "flux_gen",
        "preset": "discord_banner",
        "prompt_template": (
            "Discord server banner for ${name} ($${ticker}) community. "
            "${concept}. ${vibe} theme, welcoming but hype, "
            "dark background with ${colors} lighting effects, "
            "community vibes, crypto discord aesthetic. ${tagline}"
        ),
        "params": {"width": 960, "height": 540, "guidance": 3.5},
    },
    "promo_video_thumbnail": {
        "skill": "flux_gen",
        "preset": "youtube_1080p",
        "prompt_template": (
            "YouTube/video thumbnail for ${name} ($${ticker}) promotional video. "
            "${concept}. Maximum clickbait energy, bold text '$${ticker}', "
            "shocked face or rocket imagery, ${vibe} style, "
            "${colors} glow effects, impossible to ignore. ${tagline}"
        ),
        "params": {"width": 1920, "height": 1080, "guidance": 3.5},
    },
}


def build_prompt(template: str, token: TokenMeta) -> str:
    """Fill a prompt template with token metadata."""
    colors_str = ", ".join(token.colors)
    return (
        template.replace("${name}", token.name)
        .replace("${ticker}", token.ticker)
        .replace("${concept}", token.concept or f"A {token.vibe} memecoin")
        .replace("${vibe}", token.vibe)
        .replace("${colors}", colors_str)
        .replace("${tagline}", token.tagline)
        .replace("${chain}", token.chain)
    )


def generate_brief(token: TokenMeta, assets: list[str] | None = None) -> dict[str, Any]:
    """Generate a full pipeline brief from token metadata.

    Args:
        token: Token metadata.
        assets: Which assets to generate (None = all).

    Returns:
        A brief dict ready for run_loop().
    """
    specs = ASSET_SPECS
    if assets:
        specs = {k: v for k, v in specs.items() if k in assets}

    plan = []
    for i, (asset_name, spec) in enumerate(specs.items(), 1):
        prompt = build_prompt(spec["prompt_template"], token)
        plan.append({
            "step": i,
            "task": f"Generate {asset_name}",
            "skill": spec["skill"],
            "params": {
                "prompt": prompt,
                **spec["params"],
            },
            "asset_name": asset_name,
            "export_preset": spec.get("preset", ""),
        })

    return {
        "task": f"Generate memecoin content kit for {token.name} (${token.ticker})",
        "style": token.vibe,
        "duration_seconds": 0,
        "skills_required": list({spec["skill"] for spec in specs.values()}),
        "constraints": {
            "chain": token.chain,
            "token_name": token.name,
            "ticker": token.ticker,
        },
        "reference_assets": [],
        "template": "memecoin_launch",
        "plan_override": plan,
    }


def write_brief(token: TokenMeta, output_dir: str, assets: list[str] | None = None) -> Path:
    """Write a memecoin brief to a JSON file."""
    brief = generate_brief(token, assets)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{token.ticker.lower()}_brief.json"
    path.write_text(json.dumps(brief, indent=2))
    return path
