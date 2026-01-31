"""Integration tests for the main loop."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from museloop.config import MuseLoopConfig
from museloop.core.loop import run_loop


@pytest.fixture
def mock_llm_responses():
    """Returns a callable that produces appropriate responses per agent call."""
    call_count = [0]

    async def generate(system_prompt: str, user_message: str, **kwargs):
        call_count[0] += 1
        n = call_count[0] % 5  # Cycle through agent responses

        if n == 1:  # Memory
            return json.dumps({
                "themes": ["test"],
                "successful_approaches": [],
                "rejected_approaches": [],
                "iteration_summaries": [],
            })
        elif n == 2:  # Research
            return json.dumps({
                "context": "context",
                "style_keywords": ["test"],
                "negative_prompts": [],
                "recommendations": [],
                "references": [],
            })
        elif n == 3:  # Script
            return json.dumps({
                "plan": [{"step": 1, "task": "test", "skill": "image_gen", "params": {"prompt": "test"}}],
                "script": "Test",
                "notes": "",
            })
        elif n == 4:  # Critic
            return json.dumps({
                "score": 0.9,
                "pass": True,
                "feedback": "Excellent",
                "strengths": ["good"],
                "improvements": [],
                "priority_fixes": [],
            })
        return "{}"

    return generate


@pytest.mark.asyncio
async def test_loop_completes(sample_brief_path, config, mock_llm_responses):
    """Test that the loop runs to completion with mocked LLM."""
    mock_llm = AsyncMock()
    mock_llm.generate = mock_llm_responses
    mock_llm.generate_with_images = mock_llm_responses

    with patch("museloop.core.loop.get_llm_backend", return_value=mock_llm):
        result_path = await run_loop(str(sample_brief_path), config)
        assert isinstance(result_path, Path)
        assert result_path.exists()
