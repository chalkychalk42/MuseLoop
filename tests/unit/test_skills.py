"""Tests for skill base classes, path validation, and sanitization."""

from __future__ import annotations

import pytest

from museloop.skills.base import SkillInput, SkillOutput
from museloop.skills.editing import _validate_media_path
from museloop.skills.video_gen import _sanitize_drawtext


class TestSkillInput:
    def test_basic_input(self):
        si = SkillInput(prompt="test prompt")
        assert si.prompt == "test prompt"
        assert si.params == {}

    def test_input_with_params(self):
        si = SkillInput(prompt="test", params={"width": 512, "height": 512})
        assert si.params["width"] == 512


class TestSkillOutput:
    def test_success_output(self):
        so = SkillOutput(success=True, asset_paths=["/out.png"], metadata={"k": "v"})
        assert so.success is True
        assert so.asset_paths == ["/out.png"]

    def test_failure_output(self):
        so = SkillOutput(success=False, error="something broke")
        assert so.success is False
        assert so.error == "something broke"
        assert so.asset_paths == []

    def test_default_output(self):
        so = SkillOutput()
        assert so.success is True
        assert so.error is None


class TestPathValidation:
    def test_valid_path(self, tmp_path):
        f = tmp_path / "clip.mp4"
        f.touch()
        result = _validate_media_path(str(f))
        assert result == f.resolve()

    def test_rejects_traversal(self, tmp_path):
        with pytest.raises(ValueError, match="traversal"):
            _validate_media_path(str(tmp_path / ".." / ".." / "etc" / "passwd.mp4"))

    def test_rejects_bad_extension(self, tmp_path):
        with pytest.raises(ValueError, match="extension"):
            _validate_media_path(str(tmp_path / "payload.exe"))

    def test_allowed_extensions(self, tmp_path):
        for ext in [".mp4", ".wav", ".png", ".jpg", ".mkv"]:
            f = tmp_path / f"test{ext}"
            f.touch()
            result = _validate_media_path(str(f))
            assert result.suffix == ext


class TestDrawtextSanitization:
    def test_strips_dangerous_chars(self):
        assert "'" not in _sanitize_drawtext("it's a test")
        assert ";" not in _sanitize_drawtext("cmd;injection")
        assert "\\" not in _sanitize_drawtext("back\\slash")
        assert ":" not in _sanitize_drawtext("key:value")

    def test_truncates_long_text(self):
        long = "x" * 200
        assert len(_sanitize_drawtext(long)) == 80

    def test_normal_text_unchanged(self):
        assert _sanitize_drawtext("a cyberpunk city at night") == "a cyberpunk city at night"
