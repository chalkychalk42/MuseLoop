"""CLI entry point for MuseLoop."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from museloop import __version__

app = typer.Typer(
    name="museloop",
    help="MuseLoop — AI agent for autonomous creative multimedia pipelines.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def run(
    brief: str = typer.Argument(..., help="Path to brief JSON file or task description"),
    output_dir: str = typer.Option("./output", "--output-dir", "-o", help="Output directory"),
    max_iterations: int = typer.Option(5, "--max-iterations", "-n", help="Max loop iterations"),
    threshold: float = typer.Option(0.7, "--threshold", "-t", help="Quality score to accept"),
    template: Optional[str] = typer.Option(None, "--template", help="Workflow template name"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Plan only, skip generation"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """Execute a creative pipeline from a brief file or template."""
    import json

    from museloop.config import MuseLoopConfig
    from museloop.utils.logging import setup_logging

    setup_logging(verbose=verbose)

    # If --template is used, generate a brief from template + task description
    if template:
        from museloop.templates.registry import TemplateRegistry

        reg = TemplateRegistry()
        reg.discover()
        if not reg.has(template):
            console.print(f"[red]Error:[/red] Template '{template}' not found.")
            console.print(f"Available: {', '.join(reg.list_templates())}")
            raise typer.Exit(1)

        tmpl = reg.get(template)
        brief_dict = tmpl.to_brief(task=brief)
        import tempfile

        brief_file = Path(tempfile.mktemp(suffix=".json"))
        brief_file.write_text(json.dumps(brief_dict))
        brief = str(brief_file)
        console.print(f"[dim]Using template: {template}[/dim]")

    # Validate brief exists
    brief_path = Path(brief)
    if not brief_path.exists():
        console.print(f"[red]Error:[/red] Brief file not found: {brief_path}")
        raise typer.Exit(1)

    config = MuseLoopConfig(
        output_dir=output_dir,
        max_iterations=max_iterations,
        quality_threshold=threshold,
    )

    if dry_run:
        from museloop.core.brief import Brief

        b = Brief.from_file(brief)
        console.print("\n[bold]Brief Summary:[/bold]")
        console.print(f"  {b.summary()}")
        console.print(f"\n[dim]Dry run — no generation performed.[/dim]")
        return

    from museloop.core.loop import run_loop

    if verbose:
        # Rich TUI mode with live progress display
        from museloop.ui.progress import PipelineProgress

        progress = PipelineProgress()
        with progress:
            result_path = asyncio.run(
                run_loop(str(brief_path), config, on_event=progress.on_event)
            )
        console.print(f"\n[green bold]Done![/green bold] Output at: {result_path}")
    else:
        # Simple output mode
        console.print(f"\n[bold cyan]MuseLoop v{__version__}[/bold cyan]")
        console.print(f"Brief: {brief_path}")
        console.print(f"Output: {output_dir}")
        console.print(f"Max iterations: {max_iterations}")
        console.print(f"Quality threshold: {threshold}")
        console.print()
        result_path = asyncio.run(run_loop(str(brief_path), config))
        console.print(f"\n[green bold]Done![/green bold] Output at: {result_path}")


@app.command()
def skills(
    name: Optional[str] = typer.Argument(None, help="Skill name to inspect"),
) -> None:
    """List available skills or inspect a specific skill."""
    from museloop.skills.registry import SkillRegistry

    registry = SkillRegistry()
    registry.discover()

    if name:
        # Inspect a single skill
        if not registry.has(name):
            console.print(f"[red]Skill '{name}' not found.[/red]")
            raise typer.Exit(1)
        skill = registry.get(name)
        console.print(f"\n[bold]{skill.name}[/bold]")
        console.print(f"  {skill.description}")
    else:
        # List all skills
        details = registry.list_details()
        if not details:
            console.print("[yellow]No skills found.[/yellow]")
            return

        table = Table(title="Available Skills")
        table.add_column("Name", style="cyan")
        table.add_column("Description")
        for skill in details:
            table.add_row(skill["name"], skill["description"])
        console.print(table)


@app.command()
def inspect(
    brief: str = typer.Argument(..., help="Path to brief JSON file"),
) -> None:
    """Parse a brief and show its contents without executing."""
    from museloop.core.brief import Brief

    brief_path = Path(brief)
    if not brief_path.exists():
        console.print(f"[red]Error:[/red] Brief file not found: {brief_path}")
        raise typer.Exit(1)

    b = Brief.from_file(brief)
    console.print("\n[bold]Brief Details:[/bold]")
    console.print(f"  Task: {b.task}")
    if b.style:
        console.print(f"  Style: {b.style}")
    if b.duration_seconds:
        console.print(f"  Duration: {b.duration_seconds}s")
    if b.skills_required:
        console.print(f"  Skills: {', '.join(b.skills_required)}")
    if b.constraints:
        console.print(f"  Constraints: {b.constraints}")
    if b.reference_assets:
        console.print(f"  References: {b.reference_assets}")


@app.command()
def history(
    output_dir: str = typer.Option("./output", "--output-dir", "-o", help="Output directory"),
) -> None:
    """Show git iteration history for an output directory."""
    from museloop.versioning.git_ops import GitOps

    git = GitOps(output_dir)
    git.init()
    entries = git.get_history()

    if not entries:
        console.print("[yellow]No iteration history found.[/yellow]")
        return

    table = Table(title="Iteration History")
    table.add_column("Hash", style="dim", width=8)
    table.add_column("Date", style="cyan")
    table.add_column("Message")
    for entry in entries:
        table.add_row(entry["hash"][:8], entry["date"][:19], entry["message"])
    console.print(table)


@app.command()
def serve(
    transport: str = typer.Option("stdio", "--transport", "-T", help="MCP transport (stdio)"),
) -> None:
    """Start the MCP server for Claude Desktop/Code integration."""
    try:
        from museloop.mcp.server import init_handlers, run_server
    except ImportError:
        console.print(
            "[red]Error:[/red] MCP dependencies not installed. "
            "Install with: [cyan]uv pip install 'museloop[mcp]'[/cyan]"
        )
        raise typer.Exit(1)

    from museloop.config import MuseLoopConfig

    console.print(f"[bold cyan]MuseLoop MCP Server v{__version__}[/bold cyan]")
    console.print(f"Transport: {transport}")
    console.print("Waiting for connections...\n", style="dim")

    config = MuseLoopConfig()
    init_handlers(config)
    run_server()


@app.command()
def dashboard(
    host: str = typer.Option("127.0.0.1", "--host", "-H", help="Bind address"),
    port: int = typer.Option(8420, "--port", "-p", help="Port number"),
) -> None:
    """Launch the web dashboard."""
    try:
        import uvicorn

        from museloop.web.app import create_app
    except ImportError:
        console.print(
            "[red]Error:[/red] Web dependencies not installed. "
            "Install with: [cyan]uv pip install 'museloop[web]'[/cyan]"
        )
        raise typer.Exit(1)

    from museloop.config import MuseLoopConfig

    console.print(f"[bold cyan]MuseLoop Dashboard v{__version__}[/bold cyan]")
    console.print(f"Running at http://{host}:{port}")

    config = MuseLoopConfig()
    app_instance = create_app(config)
    uvicorn.run(app_instance, host=host, port=port, log_level="info")


@app.command()
def templates(
    name: Optional[str] = typer.Argument(None, help="Template name to inspect"),
) -> None:
    """List workflow templates or inspect a specific one."""
    from museloop.templates.registry import TemplateRegistry

    reg = TemplateRegistry()
    reg.discover()

    if name:
        if not reg.has(name):
            console.print(f"[red]Template '{name}' not found.[/red]")
            raise typer.Exit(1)
        tmpl = reg.get(name)
        console.print(f"\n[bold]{tmpl.name}[/bold] ({tmpl.category})")
        console.print(f"  {tmpl.description}")
        console.print(f"  Style: {tmpl.default_style or 'none'}")
        console.print(f"  Duration: {tmpl.duration_range[0]}-{tmpl.duration_range[1]}s")
        console.print(f"  Export: {tmpl.export.aspect_ratio} @ {tmpl.export.resolution}")
        console.print(f"  Skills: {', '.join(tmpl.default_skills)}")
        if tmpl.steps:
            console.print(f"\n  Steps:")
            for step in tmpl.steps:
                console.print(f"    {step.order}. [{step.skill}] {step.description}")
    else:
        details = reg.list_details()
        if not details:
            console.print("[yellow]No templates found. Install pyyaml for template support.[/yellow]")
            return

        table = Table(title="Workflow Templates")
        table.add_column("Name", style="cyan")
        table.add_column("Category")
        table.add_column("Description")
        for t in details:
            table.add_row(t["name"], t["category"], t["description"])
        console.print(table)


@app.command(name="export")
def export_cmd(
    input_file: str = typer.Argument(..., help="Input video/image file"),
    preset: str = typer.Option("youtube_1080p", "--preset", "-p", help="Export preset name"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    mode: str = typer.Option("fit", "--mode", "-m", help="Resize mode: fit, fill, or stretch"),
    list_presets: bool = typer.Option(False, "--list", help="List available presets"),
) -> None:
    """Export a video/image to a platform-specific format."""
    from museloop.export.presets import list_presets as _list_presets

    if list_presets:
        table = Table(title="Export Presets")
        table.add_column("Name", style="cyan")
        table.add_column("Resolution")
        table.add_column("Aspect Ratio")
        for p in _list_presets():
            table.add_row(p["name"], p["resolution"], p["aspect_ratio"])
        console.print(table)
        return

    input_path = Path(input_file)
    if not input_path.exists():
        console.print(f"[red]Error:[/red] Input file not found: {input_path}")
        raise typer.Exit(1)

    from museloop.export.renderer import ExportRenderer

    try:
        renderer = ExportRenderer(preset)
    except KeyError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    info = renderer.get_info()
    console.print(f"\n[bold cyan]Export[/bold cyan] {input_path.name}")
    console.print(f"  Preset: {info['name']} ({info['resolution']}, {info['aspect_ratio']})")
    console.print(f"  Mode: {mode}")

    try:
        result_path = renderer.render(str(input_path), output, mode=mode)
        console.print(f"\n[green bold]Done![/green bold] Output: {result_path}")
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def memecoin(
    name: str = typer.Argument(..., help="Token name (e.g., 'DogWifHat')"),
    ticker: str = typer.Argument(..., help="Ticker symbol (e.g., 'WIF')"),
    concept: str = typer.Option("", "--concept", "-c", help="What's the coin about?"),
    vibe: str = typer.Option("degen", "--vibe", help="Aesthetic: degen, cute, dark, neon, retro"),
    chain: str = typer.Option("SOL", "--chain", help="Blockchain: SOL, ETH, BASE"),
    tagline: str = typer.Option("", "--tagline", help="Project tagline"),
    output_dir: str = typer.Option("./output", "--output-dir", "-o", help="Output directory"),
    assets: Optional[str] = typer.Option(None, "--assets", help="Comma-separated asset names"),
    brief_only: bool = typer.Option(False, "--brief-only", help="Generate brief JSON only"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable Rich TUI"),
) -> None:
    """Generate a full memecoin content kit — logos, banners, memes, everything.

    Examples:
      museloop memecoin "DogWifHat" "WIF" --concept "A dog wearing a hat" --vibe degen
      museloop memecoin "PepeCoin" "PEPE" --vibe retro --chain ETH
      museloop memecoin "MoonCat" "MCAT" --assets token_logo,dexscreener_banner
    """
    from museloop.memecoin.generator import ASSET_SPECS, TokenMeta, write_brief

    token = TokenMeta(
        name=name,
        ticker=ticker,
        concept=concept,
        vibe=vibe,
        chain=chain,
        tagline=tagline,
    )

    asset_list = assets.split(",") if assets else None

    console.print(f"\n[bold magenta]MuseLoop Memecoin Kit[/bold magenta]")
    console.print(f"  Token: {name} (${ticker})")
    console.print(f"  Chain: {chain}")
    console.print(f"  Vibe: {vibe}")
    if concept:
        console.print(f"  Concept: {concept}")

    # Show what will be generated
    specs = ASSET_SPECS if not asset_list else {k: v for k, v in ASSET_SPECS.items() if k in asset_list}
    console.print(f"\n  Assets to generate ({len(specs)}):")
    for asset_name in specs:
        console.print(f"    [cyan]{asset_name}[/cyan]")

    brief_path = write_brief(token, output_dir, asset_list)
    console.print(f"\n  Brief: {brief_path}")

    if brief_only:
        console.print(f"\n[dim]Brief-only mode — no generation performed.[/dim]")
        return

    from museloop.config import MuseLoopConfig
    from museloop.core.loop import run_loop
    from museloop.utils.logging import setup_logging

    setup_logging(verbose=verbose)

    config = MuseLoopConfig(
        output_dir=output_dir,
        max_iterations=2,
        quality_threshold=0.6,
    )

    if verbose:
        from museloop.ui.progress import PipelineProgress

        progress = PipelineProgress()
        with progress:
            result_path = asyncio.run(
                run_loop(str(brief_path), config, on_event=progress.on_event)
            )
    else:
        console.print("\n  Generating...\n")
        result_path = asyncio.run(run_loop(str(brief_path), config))

    console.print(f"\n[green bold]Kit complete![/green bold] Output: {result_path}")


@app.command()
def version() -> None:
    """Show MuseLoop version."""
    console.print(f"MuseLoop v{__version__}")


if __name__ == "__main__":
    app()
