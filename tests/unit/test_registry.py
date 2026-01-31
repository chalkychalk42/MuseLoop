"""Tests for skill registry."""

from __future__ import annotations

import pytest

from museloop.skills.base import BaseSkill, SkillInput, SkillOutput
from museloop.skills.registry import SkillRegistry


class DummySkill(BaseSkill):
    name = "dummy"
    description = "A dummy skill"

    async def execute(self, input: SkillInput, config: dict) -> SkillOutput:
        return SkillOutput(success=True)


def test_registry_register():
    registry = SkillRegistry()
    registry.register(DummySkill())
    assert registry.has("dummy")
    assert not registry.has("nonexistent")


def test_registry_get():
    registry = SkillRegistry()
    registry.register(DummySkill())
    skill = registry.get("dummy")
    assert skill.name == "dummy"


def test_registry_get_missing():
    registry = SkillRegistry()
    with pytest.raises(KeyError, match="not found"):
        registry.get("nonexistent")


def test_registry_list_skills():
    registry = SkillRegistry()
    registry.register(DummySkill())
    assert "dummy" in registry.list_skills()


def test_registry_list_details():
    registry = SkillRegistry()
    registry.register(DummySkill())
    details = registry.list_details()
    assert len(details) == 1
    assert details[0]["name"] == "dummy"
    assert details[0]["description"] == "A dummy skill"


def test_registry_discover():
    """Test that the real manifests are discovered."""
    registry = SkillRegistry()
    registry.discover()
    skills = registry.list_skills()
    assert "image_gen" in skills
    assert "video_gen" in skills
    assert "audio_gen" in skills
    assert "editing" in skills
