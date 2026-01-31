"""LangGraph StateGraph builder — wires agents into the pipeline."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from museloop.agents.critic import CriticAgent
from museloop.agents.director import DirectorAgent
from museloop.agents.memory import MemoryAgent
from museloop.agents.research import ResearchAgent
from museloop.agents.script import ScriptAgent
from museloop.config import MuseLoopConfig
from museloop.core.state import LoopState
from museloop.llm.base import LLMBackend
from museloop.skills.registry import SkillRegistry


# --- Routing functions (pure, testable) ---


def should_research(state: LoopState) -> str:
    """Skip research if memory already has sufficient context from prior iterations."""
    memory = state.get("memory", {})
    if (
        state.get("iteration", 1) > 1
        and memory.get("style_keywords")
        and memory.get("recommendations")
    ):
        return "script"
    return "research"


def after_director(state: LoopState) -> str:
    """Retry director once if it produced no assets."""
    assets = state.get("assets", [])
    retries = state.get("director_retries", 0)
    # Only retry once (retries==1 means first attempt failed), cap strictly
    if not assets and retries == 1:
        return "director"
    return "critic"


def after_critic(state: LoopState) -> str:
    """Route to human approval if enabled and score is borderline."""
    critique = state.get("critique", {})
    score = critique.get("score", 0.0)
    approval = state.get("human_approval")
    # Only route to approval if no approval yet and score is borderline
    if approval is None and 0.5 < score < 0.9:
        return "human_approval"
    return END


# --- Human approval node ---


async def human_approval_node(state: LoopState) -> dict[str, Any]:
    """Pause point for human-in-the-loop approval.

    In CLI mode: auto-approves (future: stdin prompt).
    In Web/MCP mode: resolved externally via API call.
    """
    return {
        "human_approval": {"approved": True, "notes": "Auto-approved (no interactive UI)"},
    }


# --- Graph builder ---


def build_graph(
    llm: LLMBackend,
    registry: SkillRegistry,
    config: MuseLoopConfig,
) -> CompiledStateGraph:
    """Build and compile the LangGraph agent graph.

    Flow with conditional routing:
      START → memory → [research OR script] → script → director → [retry OR critic] → [approval OR END]
    """
    prompts_dir = str(config.get_prompts_path())
    output_dir = str(config.get_output_path())

    # Instantiate agents
    memory_agent = MemoryAgent(llm, prompts_dir)
    research_agent = ResearchAgent(llm, prompts_dir)
    script_agent = ScriptAgent(llm, prompts_dir)
    director_agent = DirectorAgent(llm, prompts_dir, registry, output_dir)
    critic_agent = CriticAgent(llm, prompts_dir, config.quality_threshold)

    # Build graph
    graph = StateGraph(LoopState)

    # Add agent nodes
    graph.add_node("memory", memory_agent.run)
    graph.add_node("research", research_agent.run)
    graph.add_node("script", script_agent.run)
    graph.add_node("director", director_agent.run)
    graph.add_node("critic", critic_agent.run)

    # Wire edges with conditional routing
    graph.add_edge(START, "memory")

    # Memory → conditionally skip research
    graph.add_conditional_edges("memory", should_research, {
        "research": "research",
        "script": "script",
    })
    graph.add_edge("research", "script")
    graph.add_edge("script", "director")

    # Director → retry or proceed to critic
    graph.add_conditional_edges("director", after_director, {
        "director": "director",
        "critic": "critic",
    })

    # Critic → optional human approval or END
    if config.human_in_loop:
        graph.add_node("human_approval", human_approval_node)
        graph.add_conditional_edges("critic", after_critic, {
            "human_approval": "human_approval",
            END: END,
        })
        graph.add_edge("human_approval", END)
    else:
        graph.add_edge("critic", END)

    return graph.compile()
