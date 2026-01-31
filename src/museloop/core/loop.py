"""Main agentic loop — the heart of MuseLoop."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Callable

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

# Event callback type: receives (event_name, event_data)
EventCallback = Callable[[str, dict[str, Any]], None]


def _emit(on_event: EventCallback | None, event: str, data: dict[str, Any]) -> None:
    """Safely emit an event if a callback is registered."""
    if on_event:
        try:
            on_event(event, data)
        except Exception:
            pass  # Never let callback errors break the loop


async def run_loop(
    brief_path: str,
    config: MuseLoopConfig,
    on_event: EventCallback | None = None,
) -> Path:
    """Main entry point. Runs the full agentic loop.

    1. Load brief
    2. Initialize LLM, skills, graph, git
    3. Iterate: invoke graph → commit → check quality → repeat or stop
    4. Return output directory path

    Args:
        brief_path: Path to the brief JSON file.
        config: MuseLoop configuration.
        on_event: Optional callback for progress events (used by CLI TUI, Web, MCP).
    """
    # Load and validate the brief
    brief = Brief.from_file(brief_path)
    logger.info("brief_loaded", task=brief.task, style=brief.style)
    _emit(on_event, "brief_loaded", {"task": brief.task, "style": brief.style})

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
    _emit(on_event, "skills_discovered", {"skills": registry.list_skills()})

    graph = build_graph(llm=llm, registry=registry, config=config)

    output_path = config.get_output_path()
    git = GitOps(output_path)
    git.init()

    # Initialize state with conditional flow fields
    state: dict[str, Any] = {
        "brief": brief.model_dump(),
        "iteration": 0,
        "plan": [],
        "assets": [],
        "critique": {},
        "messages": [],
        "memory": {},
        "status": "planning",
        # Conditional flow fields
        "director_retries": 0,
        "human_approval": None,
        "last_error": "",
    }

    best_score = 0.0
    best_iteration = 0
    best_state: dict[str, Any] | None = None
    all_assets: list[dict[str, Any]] = []

    for i in range(config.max_iterations):
        state["iteration"] = i + 1
        # Reset per-iteration conditional fields
        state["director_retries"] = 0
        state["human_approval"] = None

        logger.info("iteration_start", iteration=state["iteration"])
        _emit(on_event, "iteration_start", {
            "iteration": state["iteration"],
            "max_iterations": config.max_iterations,
        })

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
            _emit(on_event, "iteration_timeout", {"iteration": state["iteration"]})
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

        _emit(on_event, "iteration_complete", {
            "iteration": state["iteration"],
            "score": score,
            "passed": state.get("critique", {}).get("pass", False),
            "asset_count": len(iteration_assets),
            "best_score": best_score,
        })

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
    _emit(on_event, "loop_complete", {
        "total_iterations": state["iteration"],
        "best_score": best_score,
        "best_iteration": best_iteration,
        "total_assets": len(all_assets),
    })

    return output_path
