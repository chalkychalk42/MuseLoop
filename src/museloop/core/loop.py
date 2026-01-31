"""Main agentic loop — the heart of MuseLoop."""

from __future__ import annotations

import asyncio
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

# Maximum time (seconds) for a single graph invocation before timeout
GRAPH_TIMEOUT_SECONDS = 600


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

    # Pass relevant config to skill constructors
    skill_config = {
        "comfyui_url": config.comfyui_url or "http://localhost:8188",
        "replicate_api_key": config.replicate_api_key,
    }
    registry = SkillRegistry(skill_config=skill_config)
    registry.discover()
    logger.info(
        "skills_discovered", count=len(registry.list_skills()), skills=registry.list_skills()
    )

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
    best_state: dict[str, Any] | None = None
    all_assets: list[dict[str, Any]] = []

    for i in range(config.max_iterations):
        state["iteration"] = i + 1
        logger.info("iteration_start", iteration=state["iteration"])

        # Run the LangGraph graph with timeout protection
        try:
            result = await asyncio.wait_for(
                graph.ainvoke(state), timeout=GRAPH_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            logger.error(
                "iteration_timeout",
                iteration=state["iteration"],
                timeout=GRAPH_TIMEOUT_SECONDS,
            )
            continue

        if not isinstance(result, dict):
            logger.error("invalid_graph_result", type=type(result).__name__)
            continue

        # Accumulate assets across iterations
        iteration_assets = result.get("assets", [])
        for asset in iteration_assets:
            asset["iteration"] = i + 1
        all_assets.extend(iteration_assets)

        # Update state — keep accumulated assets
        state.update(result)
        state["assets"] = all_assets

        # Git commit this iteration's outputs
        git.commit_iteration(i + 1, iteration_assets)

        # Track best iteration (snapshot state for potential restore)
        score = state.get("critique", {}).get("score", 0.0)
        if score > best_score:
            best_score = score
            best_iteration = i + 1
            best_state = {k: v for k, v in state.items() if k != "messages"}

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

    # If the loop exhausted iterations without passing, restore best state
    if not state.get("critique", {}).get("pass", False) and best_state:
        logger.info(
            "restoring_best_iteration",
            best_iteration=best_iteration,
            best_score=best_score,
        )
        git.tag(f"best-v{best_iteration}")

    state["status"] = "complete"
    logger.info(
        "loop_complete",
        total_iterations=state["iteration"],
        best_score=best_score,
        best_iteration=best_iteration,
        total_assets=len(all_assets),
    )

    return output_path
