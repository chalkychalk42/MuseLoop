"""Tests for vision utilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from museloop.utils.vision import (
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    get_image_paths_from_assets,
    resize_for_vision,
)


class TestGetImagePathsFromAssets:
    def test_extracts_image_paths(self, tmp_path):
        img = tmp_path / "hero.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        assets = [{"type": "image", "path": str(img), "step": 1}]
        result = get_image_paths_from_assets(assets)
        assert len(result) == 1
        assert result[0] == str(img)

    def test_skips_nonexistent_paths(self):
        assets = [{"type": "image", "path": "/nonexistent/file.png", "step": 1}]
        result = get_image_paths_from_assets(assets)
        assert result == []

    def test_skips_empty_path(self):
        assets = [{"type": "image", "path": "", "step": 1}]
        result = get_image_paths_from_assets(assets)
        assert result == []

    def test_multiple_images(self, tmp_path):
        paths = []
        for i in range(3):
            img = tmp_path / f"img_{i}.jpg"
            img.write_bytes(b"\xff\xd8\xff" + b"\x00" * 50)
            paths.append(str(img))
        assets = [{"type": "image", "path": p, "step": i} for i, p in enumerate(paths)]
        result = get_image_paths_from_assets(assets)
        assert len(result) == 3

    def test_caps_at_max(self, tmp_path):
        assets = []
        for i in range(15):
            img = tmp_path / f"img_{i}.png"
            img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)
            assets.append({"type": "image", "path": str(img), "step": i})
        result = get_image_paths_from_assets(assets)
        assert len(result) == 10  # MAX_VISION_IMAGES

    def test_handles_mixed_types(self, tmp_path):
        img = tmp_path / "shot.png"
        img.write_bytes(b"\x89PNG" + b"\x00" * 50)
        assets = [
            {"type": "image", "path": str(img), "step": 1},
            {"type": "audio", "path": str(tmp_path / "music.wav"), "step": 2},
        ]
        result = get_image_paths_from_assets(assets)
        assert len(result) == 1

    def test_webp_extension(self, tmp_path):
        img = tmp_path / "shot.webp"
        img.write_bytes(b"RIFF" + b"\x00" * 50)
        assets = [{"type": "image", "path": str(img)}]
        result = get_image_paths_from_assets(assets)
        assert len(result) == 1


class TestResizeForVision:
    def test_small_image_unchanged(self, tmp_path):
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        img = Image.new("RGB", (800, 600), color=(100, 100, 100))
        path = str(tmp_path / "small.png")
        img.save(path)

        result = resize_for_vision(path)
        assert result == path  # No resize needed

    def test_large_image_resized(self, tmp_path):
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        img = Image.new("RGB", (4000, 3000), color=(100, 100, 100))
        path = str(tmp_path / "large.png")
        img.save(path)

        result = resize_for_vision(path, max_dimension=1568)
        assert result != path
        assert result.endswith(".resized.jpg")

        resized = Image.open(result)
        assert max(resized.size) <= 1568

    def test_nonexistent_returns_original(self):
        result = resize_for_vision("/nonexistent/file.png")
        assert result == "/nonexistent/file.png"
