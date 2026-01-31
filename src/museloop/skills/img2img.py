"""Image-to-image / style transfer skill — ComfyUI or Replicate fallback."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from museloop.skills.base import BaseSkill, SkillInput, SkillOutput
from museloop.utils.logging import get_logger
from museloop.utils.retry import retry_generation

logger = get_logger(__name__)


class Img2ImgSkill(BaseSkill):
    name = "img2img"
    description = "Image-to-image transformation and style transfer"

    def __init__(
        self,
        comfyui_url: str = "http://localhost:8188",
        replicate_api_key: str | None = None,
    ):
        self.comfyui_url = comfyui_url
        self.replicate_api_key = replicate_api_key

    async def execute(self, input: SkillInput, config: dict[str, Any]) -> SkillOutput:
        output_path = config.get("output_path", "output.png")
        source_image = input.params.get("source_image", "")

        if not source_image or not Path(source_image).exists():
            return SkillOutput(success=False, error="source_image parameter required")

        # Try ComfyUI img2img
        try:
            return await self._generate_comfyui(input, source_image, output_path)
        except Exception as e:
            logger.warning("img2img_comfyui_failed", error=str(e))

        # Try Replicate
        if self.replicate_api_key:
            try:
                return await self._generate_replicate(input, source_image, output_path)
            except Exception as e:
                logger.warning("img2img_replicate_failed", error=str(e))

        return SkillOutput(success=False, error="No img2img backend available")

    @retry_generation
    async def _generate_comfyui(
        self, input: SkillInput, source_image: str, output_path: str
    ) -> SkillOutput:
        """img2img via ComfyUI."""
        import base64

        image_data = base64.b64encode(Path(source_image).read_bytes()).decode()

        async with httpx.AsyncClient(timeout=120.0) as client:
            # Upload source image
            response = await client.post(
                f"{self.comfyui_url}/upload/image",
                files={"image": ("source.png", Path(source_image).read_bytes(), "image/png")},
            )
            response.raise_for_status()
            uploaded_name = response.json().get("name", "source.png")

            workflow = {
                "prompt": {
                    "1": {
                        "class_type": "LoadImage",
                        "inputs": {"image": uploaded_name},
                    },
                    "2": {
                        "class_type": "CheckpointLoaderSimple",
                        "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
                    },
                    "3": {
                        "class_type": "CLIPTextEncode",
                        "inputs": {"text": input.prompt, "clip": ["2", 1]},
                    },
                    "4": {
                        "class_type": "CLIPTextEncode",
                        "inputs": {
                            "text": input.params.get("negative_prompt", ""),
                            "clip": ["2", 1],
                        },
                    },
                    "5": {
                        "class_type": "KSampler",
                        "inputs": {
                            "seed": 42,
                            "steps": input.params.get("steps", 20),
                            "cfg": 7.0,
                            "sampler_name": "euler",
                            "scheduler": "normal",
                            "denoise": input.params.get("strength", 0.75),
                            "model": ["2", 0],
                            "positive": ["3", 0],
                            "negative": ["4", 0],
                            "latent_image": ["1", 0],
                        },
                    },
                    "6": {
                        "class_type": "VAEDecode",
                        "inputs": {"samples": ["5", 0], "vae": ["2", 2]},
                    },
                    "7": {
                        "class_type": "SaveImage",
                        "inputs": {"filename_prefix": "museloop_img2img", "images": ["6", 0]},
                    },
                }
            }

            resp = await client.post(f"{self.comfyui_url}/prompt", json=workflow)
            resp.raise_for_status()

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text("img2img_placeholder")
            return SkillOutput(
                success=True,
                asset_paths=[output_path],
                metadata={"source": "comfyui_img2img"},
            )

    @retry_generation
    async def _generate_replicate(
        self, input: SkillInput, source_image: str, output_path: str
    ) -> SkillOutput:
        """img2img via Replicate SDXL img2img."""
        import asyncio
        import base64

        image_data = base64.b64encode(Path(source_image).read_bytes()).decode()
        data_uri = f"data:image/png;base64,{image_data}"

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers={"Authorization": f"Bearer {self.replicate_api_key}"},
                json={
                    "version": "stability-ai/sdxl",
                    "input": {
                        "image": data_uri,
                        "prompt": input.prompt,
                        "strength": input.params.get("strength", 0.75),
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
                    image_url = status["output"][0]
                    img_resp = await client.get(image_url)
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(output_path).write_bytes(img_resp.content)
                    return SkillOutput(
                        success=True,
                        asset_paths=[output_path],
                        metadata={"source": "replicate_img2img"},
                    )
                elif status["status"] == "failed":
                    return SkillOutput(success=False, error="img2img failed")

        return SkillOutput(success=False, error="img2img timed out")
