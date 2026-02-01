"""Tests for workflow templates."""

from __future__ import annotations

import pytest

from museloop.templates.base import ExportSettings, TemplateStep, WorkflowTemplate
from museloop.templates.registry import TemplateRegistry


class TestWorkflowTemplate:
    def test_create_template(self):
        tmpl = WorkflowTemplate(
            name="test",
            category="testing",
            description="A test template",
            default_skills=["image_gen"],
        )
        assert tmpl.name == "test"
        assert tmpl.category == "testing"

    def test_to_brief(self):
        tmpl = WorkflowTemplate(
            name="test",
            category="testing",
            description="Test",
            default_style="cyberpunk",
            default_skills=["image_gen", "video_gen"],
            duration_range=(30, 60),
            export=ExportSettings(aspect_ratio="16:9", resolution="1920x1080"),
        )
        brief = tmpl.to_brief(task="Create a test video")
        assert brief["task"] == "Create a test video"
        assert brief["style"] == "cyberpunk"
        assert brief["duration_seconds"] == 45  # (30+60)//2
        assert brief["skills_required"] == ["image_gen", "video_gen"]
        assert brief["constraints"]["aspect_ratio"] == "16:9"
        assert brief["template"] == "test"

    def test_to_brief_override_style(self):
        tmpl = WorkflowTemplate(
            name="test",
            category="testing",
            description="Test",
            default_style="cyberpunk",
        )
        brief = tmpl.to_brief(task="Test", style="anime")
        assert brief["style"] == "anime"

    def test_steps(self):
        step = TemplateStep(order=1, skill="image_gen", description="Generate hero image")
        assert step.order == 1
        assert step.skill == "image_gen"

    def test_export_defaults(self):
        export = ExportSettings()
        assert export.aspect_ratio == "16:9"
        assert export.fps == 30


class TestTemplateRegistry:
    def test_discover_builtin(self):
        reg = TemplateRegistry()
        reg.discover()
        names = reg.list_templates()
        assert len(names) == 10
        assert "tiktok_vertical" in names
        assert "youtube_shorts" in names
        assert "trailer" in names
        assert "brand_video" in names
        assert "podcast_visual" in names
        assert "music_video" in names
        assert "social_carousel" in names
        assert "memecoin_launch" in names
        assert "memecoin_social" in names
        assert "memecoin_video" in names

    def test_get_template(self):
        reg = TemplateRegistry()
        reg.discover()
        tmpl = reg.get("trailer")
        assert tmpl.name == "trailer"
        assert tmpl.category == "cinematic"

    def test_get_missing_template(self):
        reg = TemplateRegistry()
        reg.discover()
        with pytest.raises(KeyError):
            reg.get("nonexistent")

    def test_has_template(self):
        reg = TemplateRegistry()
        reg.discover()
        assert reg.has("tiktok_vertical")
        assert not reg.has("nonexistent")

    def test_list_details(self):
        reg = TemplateRegistry()
        reg.discover()
        details = reg.list_details()
        assert len(details) == 10
        for d in details:
            assert "name" in d
            assert "category" in d
            assert "description" in d

    def test_all_templates_to_brief(self):
        """Every template should produce a valid brief."""
        reg = TemplateRegistry()
        reg.discover()
        for name in reg.list_templates():
            tmpl = reg.get(name)
            brief = tmpl.to_brief(task="Test task")
            assert brief["task"] == "Test task"
            assert "constraints" in brief
            assert "skills_required" in brief

    def test_manual_register(self):
        reg = TemplateRegistry()
        tmpl = WorkflowTemplate(name="custom", category="test", description="Custom")
        reg.register(tmpl)
        assert reg.has("custom")
