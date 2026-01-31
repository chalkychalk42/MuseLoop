"""LangGraph StateGraph builder — wires agents into the pipeline."""

from __future__ import annotations

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


def build_graph(
    llm: LLMBackend,
    registry: SkillRegistry,
    config: MuseLoopConfig,
) -> CompiledStateGraph:
    """Build and compile the LangGraph agent graph.

    Flow: START → memory → script → director → critic → END
    The outer loop (in loop.py) handles iteration/revision.
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

    # Wire edges: linear flow
    graph.add_edge(START, "memory")
    graph.add_edge("memory", "research")
    graph.add_edge("research", "script")
    graph.add_edge("script", "director")
    graph.add_edge("director", "critic")
    graph.add_edge("critic", END)

    return graph.compile()
