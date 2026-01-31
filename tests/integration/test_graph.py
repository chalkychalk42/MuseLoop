"""Integration tests for the LangGraph pipeline."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from museloop.config import MuseLoopConfig
from museloop.core.graph import build_graph
from museloop.skills.registry import SkillRegistry


@pytest.fixture
def mock_llm_for_graph():
    """Mock LLM that returns appropriate responses for each agent."""
    llm = AsyncMock()
    call_count = [0]

    async def smart_generate(system_prompt: str, user_message: str, **kwargs):
        call_count[0] += 1
        n = call_count[0]

        # Memory agent (call 1)
        if n == 1:
            return json.dumps({
                "themes": ["test"],
                "successful_approaches": [],
                "rejected_approaches": [],
                "iteration_summaries": [],
            })
        # Research agent (call 2)
        elif n == 2:
            return json.dumps({
                "context": "Test context",
                "style_keywords": ["test"],
                "negative_prompts": [],
                "recommendations": [],
                "references": [],
            })
        # Script agent (call 3)
        elif n == 3:
            return json.dumps({
                "plan": [
                    {"step": 1, "task": "test image", "skill": "mock_skill", "params": {"prompt": "test"}},
                ],
                "script": "Test script",
                "notes": "Test notes",
            })
        # Critic agent (call 4)
        elif n == 4:
            return json.dumps({
                "score": 0.8,
                "pass": True,
                "feedback": "Good",
                "strengths": ["test"],
                "improvements": [],
                "priority_fixes": [],
            })
        return "{}"

    llm.generate = smart_generate
    llm.generate_with_images = smart_generate
    return llm


@pytest.mark.asyncio
async def test_graph_compiles(mock_llm_for_graph, mock_registry, config):
    graph = build_graph(llm=mock_llm_for_graph, registry=mock_registry, config=config)
    assert graph is not None


@pytest.mark.asyncio
async def test_graph_full_pass(mock_llm_for_graph, mock_registry, config):
    graph = build_graph(llm=mock_llm_for_graph, registry=mock_registry, config=config)

    initial_state = {
        "brief": {"task": "Test", "style": "test"},
        "iteration": 1,
        "plan": [],
        "assets": [],
        "critique": {},
        "messages": [],
        "memory": {},
        "status": "planning",
        "director_retries": 0,
        "human_approval": None,
        "last_error": "",
    }

    result = await graph.ainvoke(initial_state)

    assert result["status"] is not None
    assert "plan" in result
    assert "critique" in result
    assert "memory" in result
