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
    brief: str = typer.Argument(..., help="Path to brief JSON file"),
    output_dir: str = typer.Option("./output", "--output-dir", "-o", help="Output directory"),
    max_iterations: int = typer.Option(5, "--max-iterations", "-n", help="Max loop iterations"),
    threshold: float = typer.Option(0.7, "--threshold", "-t", help="Quality score to accept"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Plan only, skip generation"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """Execute a creative pipeline from a brief file."""
    from museloop.config import MuseLoopConfig
    from museloop.utils.logging import setup_logging

    setup_logging(verbose=verbose)

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

    console.print(f"\n[bold cyan]MuseLoop v{__version__}[/bold cyan]")
    console.print(f"Brief: {brief_path}")
    console.print(f"Output: {output_dir}")
    console.print(f"Max iterations: {max_iterations}")
    console.print(f"Quality threshold: {threshold}")
    console.print()

    from museloop.core.loop import run_loop

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
def version() -> None:
    """Show MuseLoop version."""
    console.print(f"MuseLoop v{__version__}")


if __name__ == "__main__":
    app()
