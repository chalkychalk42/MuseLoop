"""Tests for new generation skills (Phase 5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from museloop.skills.base import SkillInput, SkillOutput
from museloop.skills.captions import CaptionsSkill, _format_timestamp
from museloop.skills.flux_gen import FluxGenSkill
from museloop.skills.img2img import Img2ImgSkill
from museloop.skills.tts import TTSSkill
from museloop.skills.upscale import UpscaleSkill


# --- FLUX Gen ---


class TestFluxGen:
    def test_instantiation(self):
        skill = FluxGenSkill()
        assert skill.name == "flux_gen"
        assert "FLUX" in skill.description

    @pytest.mark.asyncio
    async def test_no_backend_returns_error(self):
        skill = FluxGenSkill(replicate_api_key=None)
        result = await skill.execute(
            SkillInput(prompt="test"),
            {"output_path": "/tmp/test.png"},
        )
        assert result.success is False
        assert "No FLUX backend" in result.error


# --- Img2Img ---


class TestImg2Img:
    def test_instantiation(self):
        skill = Img2ImgSkill()
        assert skill.name == "img2img"

    @pytest.mark.asyncio
    async def test_missing_source_image(self):
        skill = Img2ImgSkill()
        result = await skill.execute(
            SkillInput(prompt="test", params={}),
            {"output_path": "/tmp/test.png"},
        )
        assert result.success is False
        assert "source_image" in result.error

    @pytest.mark.asyncio
    async def test_nonexistent_source(self):
        skill = Img2ImgSkill()
        result = await skill.execute(
            SkillInput(prompt="test", params={"source_image": "/nonexistent.png"}),
            {"output_path": "/tmp/test.png"},
        )
        assert result.success is False


# --- TTS ---


class TestTTS:
    def test_instantiation(self):
        skill = TTSSkill()
        assert skill.name == "tts"

    @pytest.mark.asyncio
    async def test_no_backend_returns_error(self):
        skill = TTSSkill(replicate_api_key=None)
        result = await skill.execute(
            SkillInput(prompt="Hello world"),
            {"output_path": "/tmp/test.wav"},
        )
        assert result.success is False
        assert "No TTS backend" in result.error


# --- Upscale ---


class TestUpscale:
    def test_instantiation(self):
        skill = UpscaleSkill()
        assert skill.name == "upscale"

    @pytest.mark.asyncio
    async def test_missing_source_image(self):
        skill = UpscaleSkill()
        result = await skill.execute(
            SkillInput(prompt="upscale", params={}),
            {"output_path": "/tmp/test.png"},
        )
        assert result.success is False
        assert "source_image" in result.error

    @pytest.mark.asyncio
    async def test_pil_upscale(self, tmp_path):
        """Test the PIL fallback upscaler with a real image."""
        from PIL import Image

        # Create a small test image
        src = tmp_path / "small.png"
        Image.new("RGB", (64, 64), color=(100, 150, 200)).save(str(src))

        skill = UpscaleSkill()
        output = str(tmp_path / "upscaled.png")
        result = await skill.execute(
            SkillInput(prompt="upscale", params={"source_image": str(src), "scale": 2}),
            {"output_path": output},
        )
        assert result.success is True
        assert Path(output).exists()
        upscaled = Image.open(output)
        assert upscaled.width == 128
        assert upscaled.height == 128


# --- Captions ---


class TestCaptions:
    def test_instantiation(self):
        skill = CaptionsSkill()
        assert skill.name == "captions"

    @pytest.mark.asyncio
    async def test_missing_source_media(self):
        skill = CaptionsSkill()
        result = await skill.execute(
            SkillInput(prompt="transcribe", params={}),
            {"output_path": "/tmp/test.srt"},
        )
        assert result.success is False
        assert "source_media" in result.error

    def test_srt_format(self):
        segments = [
            {"start": 0.0, "end": 2.5, "text": "Hello world"},
            {"start": 2.5, "end": 5.0, "text": "How are you"},
        ]
        srt = CaptionsSkill._to_srt(segments)
        assert "1" in srt
        assert "00:00:00,000 --> 00:00:02,500" in srt
        assert "Hello world" in srt
        assert "2" in srt

    def test_format_timestamp(self):
        assert _format_timestamp(0.0) == "00:00:00,000"
        assert _format_timestamp(1.5) == "00:00:01,500"
        assert _format_timestamp(3661.123) == "01:01:01,123"


# --- Skill Discovery ---


class TestSkillDiscovery:
    def test_all_new_skills_discoverable(self):
        from museloop.skills.registry import SkillRegistry

        registry = SkillRegistry()
        registry.discover()
        names = registry.list_skills()
        assert "flux_gen" in names
        assert "img2img" in names
        assert "tts" in names
        assert "upscale" in names
        assert "captions" in names
        # Original 4 + 5 new = 9
        assert len(names) == 9

    def test_all_skills_have_descriptions(self):
        from museloop.skills.registry import SkillRegistry

        registry = SkillRegistry()
        registry.discover()
        for detail in registry.list_details():
            assert detail["name"]
            assert detail["description"]
