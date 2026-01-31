"""FLUX image generation skill — Replicate FLUX Pro + local diffusers fallback."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from museloop.skills.base import BaseSkill, SkillInput, SkillOutput
from museloop.utils.logging import get_logger
from museloop.utils.retry import retry_generation

logger = get_logger(__name__)


class FluxGenSkill(BaseSkill):
    name = "flux_gen"
    description = "Generate images via FLUX Pro (Replicate) or local diffusers"

    def __init__(self, replicate_api_key: str | None = None):
        self.replicate_api_key = replicate_api_key

    async def execute(self, input: SkillInput, config: dict[str, Any]) -> SkillOutput:
        output_path = config.get("output_path", "output.png")

        # Try Replicate FLUX first
        if self.replicate_api_key:
            try:
                return await self._generate_replicate(input, output_path)
            except Exception as e:
                logger.warning("flux_replicate_failed", error=str(e))

        # Try local diffusers
        try:
            return await self._generate_local(input, output_path)
        except Exception as e:
            logger.warning("flux_local_failed", error=str(e))

        return SkillOutput(success=False, error="No FLUX backend available")

    @retry_generation
    async def _generate_replicate(self, input: SkillInput, output_path: str) -> SkillOutput:
        """Generate via Replicate FLUX Pro."""
        import asyncio

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers={"Authorization": f"Bearer {self.replicate_api_key}"},
                json={
                    "version": "black-forest-labs/flux-pro",
                    "input": {
                        "prompt": input.prompt,
                        "width": input.params.get("width", 1024),
                        "height": input.params.get("height", 1024),
                        "guidance": input.params.get("guidance", 3.5),
                        "steps": input.params.get("steps", 28),
                    },
                },
            )
            response.raise_for_status()
            prediction = response.json()

            for _ in range(180):
                await asyncio.sleep(2)
                status_resp = await client.get(
                    prediction["urls"]["get"],
                    headers={"Authorization": f"Bearer {self.replicate_api_key}"},
                )
                status = status_resp.json()
                if status["status"] == "succeeded":
                    image_url = status["output"]
                    if isinstance(image_url, list):
                        image_url = image_url[0]
                    img_resp = await client.get(image_url)
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(output_path).write_bytes(img_resp.content)
                    return SkillOutput(
                        success=True,
                        asset_paths=[output_path],
                        metadata={"source": "replicate_flux"},
                    )
                elif status["status"] == "failed":
                    return SkillOutput(success=False, error=status.get("error", "FLUX failed"))

        return SkillOutput(success=False, error="FLUX generation timed out")

    async def _generate_local(self, input: SkillInput, output_path: str) -> SkillOutput:
        """Generate via local diffusers pipeline."""
        try:
            import torch
            from diffusers import FluxPipeline
        except ImportError:
            raise RuntimeError("diffusers/torch not installed — install with [gpu] extra")

        pipe = FluxPipeline.from_pretrained(
            "black-forest-labs/FLUX.1-schnell",
            torch_dtype=torch.bfloat16,
        )
        pipe.to("cuda" if torch.cuda.is_available() else "cpu")

        image = pipe(
            input.prompt,
            width=input.params.get("width", 1024),
            height=input.params.get("height", 1024),
            guidance_scale=input.params.get("guidance", 0.0),
            num_inference_steps=input.params.get("steps", 4),
        ).images[0]

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path)

        return SkillOutput(
            success=True,
            asset_paths=[output_path],
            metadata={"source": "local_flux"},
        )
