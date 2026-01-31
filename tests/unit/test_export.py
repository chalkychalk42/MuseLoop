"""Tests for the export pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from museloop.export.presets import PRESETS, ExportPreset, get_preset, list_presets
from museloop.export.renderer import ExportRenderer


# --- Preset tests ---


class TestExportPreset:
    def test_preset_fields(self):
        p = ExportPreset(
            name="test",
            width=1920,
            height=1080,
            aspect_ratio="16:9",
        )
        assert p.width == 1920
        assert p.height == 1080
        assert p.fps == 30  # default
        assert p.video_codec == "libx264"

    def test_preset_immutable(self):
        p = ExportPreset(name="test", width=1920, height=1080, aspect_ratio="16:9")
        with pytest.raises(AttributeError):
            p.width = 1280  # frozen dataclass

    def test_get_preset(self):
        p = get_preset("youtube_1080p")
        assert p.name == "youtube_1080p"
        assert p.width == 1920
        assert p.height == 1080

    def test_get_preset_missing(self):
        with pytest.raises(KeyError, match="not found"):
            get_preset("nonexistent")

    def test_list_presets(self):
        presets = list_presets()
        assert len(presets) == len(PRESETS)
        for p in presets:
            assert "name" in p
            assert "resolution" in p
            assert "aspect_ratio" in p


class TestBuiltinPresets:
    def test_youtube_1080p(self):
        p = PRESETS["youtube_1080p"]
        assert p.width == 1920
        assert p.height == 1080
        assert p.aspect_ratio == "16:9"

    def test_instagram_reels(self):
        p = PRESETS["instagram_reels"]
        assert p.width == 1080
        assert p.height == 1920
        assert p.aspect_ratio == "9:16"

    def test_tiktok(self):
        p = PRESETS["tiktok"]
        assert p.width == 1080
        assert p.height == 1920

    def test_twitter(self):
        p = PRESETS["twitter"]
        assert p.width == 1280
        assert p.height == 720

    def test_instagram_square(self):
        p = PRESETS["instagram_square"]
        assert p.width == 1080
        assert p.height == 1080
        assert p.aspect_ratio == "1:1"

    def test_youtube_4k(self):
        p = PRESETS["youtube_4k"]
        assert p.width == 3840
        assert p.height == 2160

    def test_all_presets_valid(self):
        for name, p in PRESETS.items():
            assert p.width > 0
            assert p.height > 0
            assert p.fps > 0
            assert p.video_codec
            assert p.audio_codec


# --- Renderer tests ---


class TestExportRenderer:
    def test_init_with_preset_name(self):
        r = ExportRenderer("youtube_1080p")
        assert r.preset.name == "youtube_1080p"

    def test_init_with_preset_object(self):
        p = ExportPreset(name="custom", width=800, height=600, aspect_ratio="4:3")
        r = ExportRenderer(p)
        assert r.preset.name == "custom"

    def test_init_invalid_preset(self):
        with pytest.raises(KeyError):
            ExportRenderer("nonexistent")

    def test_get_info(self):
        r = ExportRenderer("tiktok")
        info = r.get_info()
        assert info["name"] == "tiktok"
        assert info["resolution"] == "1080x1920"
        assert info["aspect_ratio"] == "9:16"

    def test_build_filter_fit(self):
        r = ExportRenderer("youtube_1080p")
        vf = r._build_video_filter("fit")
        assert "scale=1920:1080" in vf
        assert "pad=" in vf

    def test_build_filter_fill(self):
        r = ExportRenderer("youtube_1080p")
        vf = r._build_video_filter("fill")
        assert "crop=1920:1080" in vf

    def test_build_filter_stretch(self):
        r = ExportRenderer("youtube_1080p")
        vf = r._build_video_filter("stretch")
        assert vf == "scale=1920:1080"

    def test_render_missing_input(self):
        r = ExportRenderer("youtube_1080p")
        with pytest.raises(FileNotFoundError):
            r.render("/nonexistent/video.mp4")

    def test_render_image_missing_input(self):
        r = ExportRenderer("youtube_1080p")
        with pytest.raises(FileNotFoundError):
            r.render_image("/nonexistent/image.png")

    def test_render_with_ffmpeg(self, tmp_path):
        """Test rendering (mocks ffmpeg subprocess)."""
        src = tmp_path / "input.mp4"
        src.write_text("fake video")
        output = str(tmp_path / "output.mp4")

        r = ExportRenderer("youtube_1080p")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            result = r.render(str(src), output)
            assert result == output
            mock_run.assert_called_once()
            # Verify ffmpeg command structure
            cmd = mock_run.call_args[0][0]
            assert cmd[0] == "ffmpeg"
            assert "-vf" in cmd
            assert "-c:v" in cmd

    def test_render_auto_output_path(self, tmp_path):
        """Auto-generated output path includes preset name."""
        src = tmp_path / "input.mp4"
        src.write_text("fake")

        r = ExportRenderer("tiktok")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            result = r.render(str(src))
            assert "tiktok" in result
