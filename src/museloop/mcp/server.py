"""MCP server for MuseLoop — exposes tools via stdio transport."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from museloop.config import MuseLoopConfig
from museloop.mcp.handlers import MCPHandlers

# --- Server instance ---

mcp_server = FastMCP(
    "MuseLoop",
    instructions=(
        "MuseLoop is an AI-powered creative multimedia pipeline. "
        "Use these tools to generate images, audio, video, and run full "
        "creative production pipelines from natural-language briefs."
    ),
)

# Handlers are initialized lazily on first tool call
_handlers: MCPHandlers | None = None


def _get_handlers() -> MCPHandlers:
    """Lazy-init handlers so config is loaded at call time."""
    global _handlers
    if _handlers is None:
        _handlers = MCPHandlers()
    return _handlers


def init_handlers(config: MuseLoopConfig | None = None) -> None:
    """Explicitly initialize handlers (for testing or custom config)."""
    global _handlers
    _handlers = MCPHandlers(config=config)


# --- Tools ---


@mcp_server.tool()
async def museloop_run(
    task: str,
    style: str = "",
    max_iterations: int = 5,
    quality_threshold: float = 0.7,
) -> str:
    """Start a full MuseLoop creative pipeline.

    Launches an autonomous multi-agent loop that plans, generates, and critiques
    multimedia content based on the task description.

    Args:
        task: What to create (e.g., "A cyberpunk city timelapse with neon rain").
        style: Visual/audio style (e.g., "cinematic", "lo-fi", "anime").
        max_iterations: Maximum generation-critique cycles (1-10).
        quality_threshold: Minimum quality score to accept (0.0-1.0).

    Returns:
        Job ID and status. Use museloop_status to check progress.
    """
    handlers = _get_handlers()
    result = await handlers.run_pipeline(
        task=task,
        style=style,
        max_iterations=max_iterations,
        quality_threshold=quality_threshold,
    )
    return _format_result(result)


@mcp_server.tool()
async def museloop_generate_image(
    prompt: str,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
) -> str:
    """Generate a single image.

    Uses the configured image generation backend (ComfyUI/Stable Diffusion or Replicate).

    Args:
        prompt: Image description (e.g., "A sunset over a mountain lake, oil painting style").
        negative_prompt: What to avoid (e.g., "blurry, low quality").
        width: Image width in pixels.
        height: Image height in pixels.

    Returns:
        Path to the generated image file and metadata.
    """
    handlers = _get_handlers()
    result = await handlers.generate_image(
        prompt=prompt,
        negative_prompt=negative_prompt,
        width=width,
        height=height,
    )
    return _format_result(result)


@mcp_server.tool()
async def museloop_generate_audio(
    prompt: str,
    duration_seconds: int = 10,
) -> str:
    """Generate audio from a text description.

    Args:
        prompt: Audio description (e.g., "Ambient rain sounds with distant thunder").
        duration_seconds: Audio length in seconds.

    Returns:
        Path to the generated audio file and metadata.
    """
    handlers = _get_handlers()
    result = await handlers.generate_audio(
        prompt=prompt,
        duration_seconds=duration_seconds,
    )
    return _format_result(result)


@mcp_server.tool()
async def museloop_skills() -> str:
    """List all available generation skills.

    Returns the names and descriptions of all registered skills (image generation,
    audio generation, video generation, editing, etc.).
    """
    handlers = _get_handlers()
    skills = handlers.list_skills()
    if not skills:
        return "No skills found. Check that skill manifests are in the correct directory."
    lines = ["Available skills:"]
    for s in skills:
        lines.append(f"  - {s['name']}: {s['description']}")
    return "\n".join(lines)


@mcp_server.tool()
async def museloop_status(job_id: str) -> str:
    """Check the status of a running or completed pipeline job.

    Args:
        job_id: The job ID returned by museloop_run.

    Returns:
        Current status, iteration progress, quality score, and asset count.
    """
    handlers = _get_handlers()
    result = handlers.get_job_status(job_id)
    return _format_result(result)


@mcp_server.tool()
async def museloop_approve(
    job_id: str,
    approved: bool = True,
    notes: str = "",
) -> str:
    """Approve or reject a pipeline job that is awaiting human review.

    Some pipeline runs pause for human-in-the-loop approval when the quality
    score is borderline. Use this tool to approve or reject and continue.

    Args:
        job_id: The job ID to approve.
        approved: True to approve, False to reject and re-iterate.
        notes: Optional feedback notes for the next iteration.
    """
    handlers = _get_handlers()
    result = handlers.approve_job(job_id, approved=approved, notes=notes)
    return _format_result(result)


@mcp_server.tool()
async def museloop_jobs() -> str:
    """List all pipeline jobs (running, completed, and failed).

    Returns a summary of each job including status, score, and asset count.
    """
    handlers = _get_handlers()
    jobs = handlers.list_jobs()
    if not jobs:
        return "No jobs found."
    import json

    return json.dumps(jobs, indent=2)


# --- Helpers ---


def _format_result(result: dict[str, Any]) -> str:
    """Format a result dict as readable text."""
    import json

    return json.dumps(result, indent=2, default=str)


def run_server() -> None:
    """Start the MCP server with stdio transport."""
    mcp_server.run(transport="stdio")
