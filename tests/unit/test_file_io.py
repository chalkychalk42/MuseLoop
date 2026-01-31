"""Tests for file I/O utilities."""

from __future__ import annotations

from pathlib import Path

from museloop.utils.file_io import asset_path, ensure_dir, iteration_dir


def test_ensure_dir(tmp_path: Path):
    new_dir = tmp_path / "a" / "b" / "c"
    result = ensure_dir(new_dir)
    assert result.exists()
    assert result.is_dir()


def test_iteration_dir(tmp_path: Path):
    idir = iteration_dir(tmp_path, 1)
    assert idir.exists()
    assert idir.name == "iteration-001"


def test_asset_path(tmp_path: Path):
    path = asset_path(tmp_path, 1, "hero-image", "png")
    assert path.name == "hero-image.png"
    assert "iteration-001" in str(path)
