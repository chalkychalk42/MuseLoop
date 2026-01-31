"""Image generation skill — ComfyUI local + Replicate API fallback."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from museloop.skills.base import BaseSkill, SkillInput, SkillOutput
from museloop.utils.logging import get_logger
from museloop.utils.retry import retry_generation

logger = get_logger(__name__)


class ImageGenSkill(BaseSkill):
    name = "image_gen"
    description = "Generate images via Stable Diffusion (ComfyUI) or Replicate API"

    def __init__(
        self,
        comfyui_url: str = "http://localhost:8188",
        replicate_api_key: str | None = None,
    ):
        self.comfyui_url = comfyui_url
        self.replicate_api_key = replicate_api_key

    async def execute(self, input: SkillInput, config: dict[str, Any]) -> SkillOutput:
        """Generate an image. Tries ComfyUI first, falls back to Replicate."""
        output_path = config.get("output_path", "output.png")

        # Try ComfyUI first
        try:
            return await self._generate_comfyui(input, output_path)
        except Exception as e:
            logger.warning("comfyui_failed", error=str(e))

        # Fallback to Replicate
        if self.replicate_api_key:
            try:
                return await self._generate_replicate(input, output_path)
            except Exception as e:
                logger.warning("replicate_failed", error=str(e))

        # Both failed — return a placeholder
        return await self._generate_placeholder(input, output_path)

    @retry_generation
    async def _generate_comfyui(self, input: SkillInput, output_path: str) -> SkillOutput:
        """Generate image via ComfyUI HTTP API."""
        workflow = {
            "prompt": {
                "3": {
                    "class_type": "KSampler",
                    "inputs": {
                        "seed": 42,
                        "steps": 20,
                        "cfg": 7.0,
                        "sampler_name": "euler",
                        "scheduler": "normal",
                        "denoise": 1.0,
                        "model": ["4", 0],
                        "positive": ["6", 0],
                        "negative": ["7", 0],
                        "latent_image": ["5", 0],
                    },
                },
                "4": {
                    "class_type": "CheckpointLoaderSimple",
                    "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
                },
                "5": {
                    "class_type": "EmptyLatentImage",
                    "inputs": {
                        "width": input.params.get("width", 1024),
                        "height": input.params.get("height", 1024),
                        "batch_size": 1,
                    },
                },
                "6": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {"text": input.prompt, "clip": ["4", 1]},
                },
                "7": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {
                        "text": input.params.get("negative_prompt", "blurry, low quality"),
                        "clip": ["4", 1],
                    },
                },
                "8": {
                    "class_type": "VAEDecode",
                    "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
                },
                "9": {
                    "class_type": "SaveImage",
                    "inputs": {"filename_prefix": "museloop", "images": ["8", 0]},
                },
            }
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            # Queue the prompt
            response = await client.post(f"{self.comfyui_url}/prompt", json=workflow)
            response.raise_for_status()
            prompt_id = response.json()["prompt_id"]

            # Poll for completion
            import asyncio

            for _ in range(120):  # 2 minute timeout
                await asyncio.sleep(1)
                history = await client.get(f"{self.comfyui_url}/history/{prompt_id}")
                if history.status_code == 200:
                    data = history.json()
                    if prompt_id in data:
                        outputs = data[prompt_id].get("outputs", {})
                        if "9" in outputs:
                            images = outputs["9"]["images"]
                            if images:
                                img_info = images[0]
                                img_url = (
                                    f"{self.comfyui_url}/view?"
                                    f"filename={img_info['filename']}"
                                    f"&subfolder={img_info.get('subfolder', '')}"
                                    f"&type={img_info.get('type', 'output')}"
                                )
                                img_response = await client.get(img_url)
                                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                                Path(output_path).write_bytes(img_response.content)
                                return SkillOutput(
                                    success=True,
                                    asset_paths=[output_path],
                                    metadata={"source": "comfyui", "prompt_id": prompt_id},
                                )

        return SkillOutput(success=False, error="ComfyUI generation timed out")

    @retry_generation
    async def _generate_replicate(self, input: SkillInput, output_path: str) -> SkillOutput:
        """Generate image via Replicate API (SDXL)."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Create prediction
            response = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers={"Authorization": f"Bearer {self.replicate_api_key}"},
                json={
                    "version": "39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
                    "input": {
                        "prompt": input.prompt,
                        "negative_prompt": input.params.get("negative_prompt", ""),
                        "width": input.params.get("width", 1024),
                        "height": input.params.get("height", 1024),
                    },
                },
            )
            response.raise_for_status()
            prediction = response.json()

            # Poll for completion
            import asyncio

            for _ in range(120):
                await asyncio.sleep(2)
                status_response = await client.get(
                    prediction["urls"]["get"],
                    headers={"Authorization": f"Bearer {self.replicate_api_key}"},
                )
                status = status_response.json()
                if status["status"] == "succeeded":
                    image_url = status["output"][0]
                    img_response = await client.get(image_url)
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(output_path).write_bytes(img_response.content)
                    return SkillOutput(
                        success=True,
                        asset_paths=[output_path],
                        metadata={"source": "replicate"},
                    )
                elif status["status"] == "failed":
                    return SkillOutput(success=False, error=status.get("error", "Replicate failed"))

        return SkillOutput(success=False, error="Replicate generation timed out")

    async def _generate_placeholder(self, input: SkillInput, output_path: str) -> SkillOutput:
        """Generate a placeholder image when no backends are available."""
        try:
            from PIL import Image, ImageDraw, ImageFont

            width = input.params.get("width", 1024)
            height = input.params.get("height", 1024)
            img = Image.new("RGB", (width, height), color=(30, 30, 40))
            draw = ImageDraw.Draw(img)

            # Draw placeholder text
            text = f"[MuseLoop Placeholder]\n{input.prompt[:80]}"
            draw.text((width // 8, height // 3), text, fill=(180, 180, 200))

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path)

            return SkillOutput(
                success=True,
                asset_paths=[output_path],
                metadata={"source": "placeholder"},
            )
        except Exception as e:
            return SkillOutput(success=False, error=f"Placeholder generation failed: {e}")
