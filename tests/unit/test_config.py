"""Tests for configuration loading."""

from __future__ import annotations

from museloop.config import MuseLoopConfig


def test_config_defaults():
    config = MuseLoopConfig(anthropic_api_key="test")
    assert config.llm_backend == "claude"
    assert config.max_iterations == 5
    assert config.quality_threshold == 0.7


def test_config_custom_values():
    config = MuseLoopConfig(
        anthropic_api_key="test",
        max_iterations=10,
        quality_threshold=0.9,
        output_dir="/custom/output",
    )
    assert config.max_iterations == 10
    assert config.quality_threshold == 0.9
    assert config.output_dir == "/custom/output"


def test_config_output_path(tmp_path):
    config = MuseLoopConfig(
        anthropic_api_key="test",
        output_dir=str(tmp_path / "output"),
    )
    path = config.get_output_path()
    assert path.exists()
