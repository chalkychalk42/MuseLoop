"""Tests for brief parsing and validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from museloop.core.brief import Brief


def test_brief_from_dict(sample_brief_dict: dict):
    brief = Brief(**sample_brief_dict)
    assert brief.task == "Test trailer"
    assert brief.style == "cyberpunk"
    assert brief.duration_seconds == 30
    assert "image_gen" in brief.skills_required


def test_brief_from_file(sample_brief_path: Path):
    brief = Brief.from_file(sample_brief_path)
    assert brief.task == "Test trailer"
    assert brief.style == "cyberpunk"


def test_brief_from_file_not_found():
    with pytest.raises(FileNotFoundError):
        Brief.from_file("/nonexistent/path.json")


def test_brief_from_file_not_json(tmp_path: Path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("not json")
    with pytest.raises(ValueError, match="JSON"):
        Brief.from_file(txt_file)


def test_brief_minimal():
    brief = Brief(task="Simple task")
    assert brief.task == "Simple task"
    assert brief.style is None
    assert brief.skills_required == []


def test_brief_summary(sample_brief_dict: dict):
    brief = Brief(**sample_brief_dict)
    summary = brief.summary()
    assert "Test trailer" in summary
    assert "cyberpunk" in summary
    assert "30s" in summary


def test_brief_invalid_missing_task():
    with pytest.raises(Exception):
        Brief()
