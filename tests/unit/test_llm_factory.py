"""Tests for LLM factory."""

from __future__ import annotations

import pytest

from museloop.config import MuseLoopConfig
from museloop.llm.claude import ClaudeBackend
from museloop.llm.factory import get_llm_backend
from museloop.llm.openai_compat import OpenAICompatBackend


def test_factory_claude():
    config = MuseLoopConfig(
        anthropic_api_key="test-key-123",
        llm_backend="claude",
    )
    backend = get_llm_backend(config)
    assert isinstance(backend, ClaudeBackend)


def test_factory_claude_missing_key():
    config = MuseLoopConfig(
        anthropic_api_key="",
        llm_backend="claude",
    )
    with pytest.raises(ValueError, match="MUSELOOP_ANTHROPIC_API_KEY"):
        get_llm_backend(config)


def test_factory_openai():
    config = MuseLoopConfig(
        llm_backend="openai",
        openai_base_url="http://localhost:11434/v1",
    )
    backend = get_llm_backend(config)
    assert isinstance(backend, OpenAICompatBackend)


def test_factory_unknown_backend():
    config = MuseLoopConfig(
        llm_backend="gpt-99",
    )
    with pytest.raises(ValueError, match="Unknown LLM backend"):
        get_llm_backend(config)
