"""Tests for individual agents."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from museloop.agents.memory import MemoryAgent
from museloop.agents.script import ScriptAgent
from museloop.agents.critic import CriticAgent
from museloop.agents.research import ResearchAgent


@pytest.fixture
def base_state():
    return {
        "brief": {"task": "Test trailer", "style": "cyberpunk"},
        "iteration": 1,
        "plan": [],
        "assets": [],
        "critique": {},
        "messages": [],
        "memory": {},
        "status": "planning",
    }


@pytest.mark.asyncio
async def test_memory_agent_first_iteration(mock_llm, base_state):
    agent = MemoryAgent(mock_llm, prompts_dir="./prompts")
    result = await agent.run(base_state)
    assert "memory" in result
    assert "themes" in result["memory"]
    assert result["status"] == "planning"


@pytest.mark.asyncio
async def test_memory_agent_subsequent_iteration(mock_llm, base_state):
    base_state["iteration"] = 2
    base_state["critique"] = {"score": 0.5, "feedback": "Needs improvement"}
    mock_llm.generate = AsyncMock(
        return_value=json.dumps({
            "themes": ["cyberpunk"],
            "successful_approaches": ["dark palette"],
            "rejected_approaches": [],
            "iteration_summaries": ["First pass decent"],
        })
    )
    agent = MemoryAgent(mock_llm, prompts_dir="./prompts")
    result = await agent.run(base_state)
    assert "memory" in result
    assert "cyberpunk" in result["memory"]["themes"]


@pytest.mark.asyncio
async def test_script_agent(mock_llm, base_state):
    mock_llm.generate = AsyncMock(
        return_value=json.dumps({
            "plan": [
                {"step": 1, "task": "hero shot", "skill": "image_gen", "params": {"prompt": "cyberpunk city"}},
            ],
            "script": "A dark neon city...",
            "notes": "Focus on atmosphere",
        })
    )
    agent = ScriptAgent(mock_llm, prompts_dir="./prompts")
    result = await agent.run(base_state)
    assert "plan" in result
    assert len(result["plan"]) == 1
    assert result["status"] == "generating"


@pytest.mark.asyncio
async def test_script_agent_handles_bad_json(mock_llm, base_state):
    mock_llm.generate = AsyncMock(return_value="not valid json at all")
    agent = ScriptAgent(mock_llm, prompts_dir="./prompts")
    result = await agent.run(base_state)
    # Should return a fallback plan
    assert "plan" in result
    assert len(result["plan"]) >= 1


@pytest.mark.asyncio
async def test_critic_agent_pass(mock_llm, base_state):
    base_state["assets"] = [
        {"type": "image", "path": "/test.png", "step": 1, "metadata": {}},
    ]
    mock_llm.generate = AsyncMock(
        return_value=json.dumps({
            "score": 0.85,
            "pass": True,
            "feedback": "Excellent work",
            "strengths": ["Great atmosphere"],
            "improvements": [],
            "priority_fixes": [],
        })
    )
    agent = CriticAgent(mock_llm, prompts_dir="./prompts", quality_threshold=0.7)
    result = await agent.run(base_state)
    assert result["critique"]["pass"] is True
    assert result["critique"]["score"] >= 0.7


@pytest.mark.asyncio
async def test_critic_agent_fail(mock_llm, base_state):
    base_state["assets"] = [
        {"type": "image", "path": "/test.png", "step": 1, "metadata": {}},
    ]
    mock_llm.generate = AsyncMock(
        return_value=json.dumps({
            "score": 0.3,
            "pass": False,
            "feedback": "Needs work",
            "strengths": [],
            "improvements": ["Better composition"],
            "priority_fixes": ["Redo hero shot"],
        })
    )
    agent = CriticAgent(mock_llm, prompts_dir="./prompts", quality_threshold=0.7)
    result = await agent.run(base_state)
    assert result["critique"]["pass"] is False
    assert result["critique"]["score"] < 0.7


@pytest.mark.asyncio
async def test_critic_no_assets(mock_llm, base_state):
    agent = CriticAgent(mock_llm, prompts_dir="./prompts")
    result = await agent.run(base_state)
    assert result["critique"]["score"] == 0.0
    assert result["critique"]["pass"] is False


@pytest.mark.asyncio
async def test_research_agent(mock_llm, base_state):
    mock_llm.generate = AsyncMock(
        return_value=json.dumps({
            "context": "Cyberpunk aesthetics...",
            "style_keywords": ["neon", "rain", "hologram"],
            "negative_prompts": ["blurry"],
            "recommendations": ["Use high contrast"],
            "references": [],
        })
    )
    agent = ResearchAgent(mock_llm, prompts_dir="./prompts")
    result = await agent.run(base_state)
    assert "memory" in result
    assert "style_keywords" in result["memory"]
