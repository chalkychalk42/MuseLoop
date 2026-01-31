"""LangGraph shared state definition."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class LoopState(TypedDict):
    """Central state shared across all agents in the LangGraph graph.

    Each agent reads from this state and returns a dict of updates.
    LangGraph merges the updates automatically.
    """

    # The brief (set once at load time)
    brief: dict[str, Any]

    # Current iteration number (1-indexed)
    iteration: int

    # Plan: list of tasks broken down by ScriptAgent
    plan: list[dict[str, Any]]

    # Generated assets from current iteration
    assets: list[dict[str, Any]]

    # Critique results from CriticAgent
    critique: dict[str, Any]

    # Conversation messages (agent reasoning traces)
    messages: Annotated[list, add_messages]

    # Persistent memory across iterations
    memory: dict[str, Any]

    # Current status
    status: str  # "planning" | "generating" | "critiquing" | "revising" | "complete"

    # --- Conditional flow fields ---

    # Director retry counter (for conditional retry on empty assets)
    director_retries: int

    # Human-in-the-loop approval result
    human_approval: dict[str, Any] | None

    # Error info for routing decisions
    last_error: str
