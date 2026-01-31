"""Image upscaling skill — Real-ESRGAN local + Replicate fallback."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from museloop.skills.base import BaseSkill, SkillInput, SkillOutput
from museloop.utils.logging import get_logger
from museloop.utils.retry import retry_generation

logger = get_logger(__name__)


class UpscaleSkill(BaseSkill):
    name = "upscale"
    description = "Upscale images via Real-ESRGAN or Replicate"

    def __init__(self, replicate_api_key: str | None = None):
        self.replicate_api_key = replicate_api_key

    async def execute(self, input: SkillInput, config: dict[str, Any]) -> SkillOutput:
        output_path = config.get("output_path", "output.png")
        source_image = input.params.get("source_image", "")

        if not source_image or not Path(source_image).exists():
            return SkillOutput(success=False, error="source_image parameter required")

        # Try Replicate upscaling
        if self.replicate_api_key:
            try:
                return await self._upscale_replicate(source_image, output_path, input)
            except Exception as e:
                logger.warning("upscale_replicate_failed", error=str(e))

        # Try local PIL-based upscale (basic bicubic, no model)
        try:
            return await self._upscale_pil(source_image, output_path, input)
        except Exception as e:
            logger.warning("upscale_pil_failed", error=str(e))

        return SkillOutput(success=False, error="No upscale backend available")

    @retry_generation
    async def _upscale_replicate(
        self, source_image: str, output_path: str, input: SkillInput
    ) -> SkillOutput:
        """Upscale via Replicate Real-ESRGAN."""
        import asyncio
        import base64

        image_data = base64.b64encode(Path(source_image).read_bytes()).decode()
        data_uri = f"data:image/png;base64,{image_data}"

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers={"Authorization": f"Bearer {self.replicate_api_key}"},
                json={
                    "version": "nightmareai/real-esrgan",
                    "input": {
                        "image": data_uri,
                        "scale": input.params.get("scale", 4),
                        "face_enhance": input.params.get("face_enhance", False),
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
                    out_url = status["output"]
                    if isinstance(out_url, list):
                        out_url = out_url[0]
                    img_resp = await client.get(out_url)
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(output_path).write_bytes(img_resp.content)
                    return SkillOutput(
                        success=True,
                        asset_paths=[output_path],
                        metadata={"source": "replicate_esrgan", "scale": input.params.get("scale", 4)},
                    )
                elif status["status"] == "failed":
                    return SkillOutput(success=False, error="Upscale failed")

        return SkillOutput(success=False, error="Upscale timed out")

    async def _upscale_pil(
        self, source_image: str, output_path: str, input: SkillInput
    ) -> SkillOutput:
        """Basic upscale via PIL (bicubic interpolation)."""
        from PIL import Image

        scale = input.params.get("scale", 4)
        img = Image.open(source_image)
        new_size = (img.width * scale, img.height * scale)
        upscaled = img.resize(new_size, Image.LANCZOS)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        upscaled.save(output_path)

        return SkillOutput(
            success=True,
            asset_paths=[output_path],
            metadata={"source": "pil_lanczos", "scale": scale},
        )
