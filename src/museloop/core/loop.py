"""Main agentic loop — the heart of MuseLoop."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from museloop.config import MuseLoopConfig
from museloop.core.brief import Brief
from museloop.core.graph import build_graph
from museloop.core.state import LoopState
from museloop.llm.factory import get_llm_backend
from museloop.skills.registry import SkillRegistry
from museloop.utils.logging import get_logger
from museloop.versioning.git_ops import GitOps

logger = get_logger(__name__)


async def run_loop(brief_path: str, config: MuseLoopConfig) -> Path:
    """Main entry point. Runs the full agentic loop.

    1. Load brief
    2. Initialize LLM, skills, graph, git
    3. Iterate: invoke graph → commit → check quality → repeat or stop
    4. Return output directory path
    """
    # Load and validate the brief
    brief = Brief.from_file(brief_path)
    logger.info("brief_loaded", task=brief.task, style=brief.style)

    # Initialize components
    llm = get_llm_backend(config)
    registry = SkillRegistry()
    registry.discover()
    logger.info("skills_discovered", count=len(registry.list_skills()), skills=registry.list_skills())

    graph = build_graph(llm=llm, registry=registry, config=config)

    output_path = config.get_output_path()
    git = GitOps(output_path)
    git.init()

    # Initialize state
    state: dict[str, Any] = {
        "brief": brief.model_dump(),
        "iteration": 0,
        "plan": [],
        "assets": [],
        "critique": {},
        "messages": [],
        "memory": {},
        "status": "planning",
    }

    best_score = 0.0
    best_iteration = 0

    for i in range(config.max_iterations):
        state["iteration"] = i + 1
        logger.info("iteration_start", iteration=state["iteration"])

        # Run the LangGraph graph for one full pass
        result = await graph.ainvoke(state)

        # Update state with graph results
        state.update(result)

        # Git commit this iteration's outputs
        git.commit_iteration(i + 1, state.get("assets", []))

        # Track best iteration
        score = state.get("critique", {}).get("score", 0.0)
        if score > best_score:
            best_score = score
            best_iteration = i + 1

        # Check if CriticAgent accepted
        if state.get("critique", {}).get("pass", False):
            logger.info(
                "quality_threshold_met",
                score=score,
                iteration=state["iteration"],
            )
            break

        logger.info(
            "iteration_complete",
            iteration=state["iteration"],
            score=score,
            passed=False,
        )

    state["status"] = "complete"
    logger.info(
        "loop_complete",
        total_iterations=state["iteration"],
        best_score=best_score,
        best_iteration=best_iteration,
    )

    return output_path
