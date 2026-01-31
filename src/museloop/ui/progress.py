"""Rich Live progress display for the pipeline."""

from __future__ import annotations

from typing import Any

from rich.console import Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text


class PipelineProgress:
    """Real-time TUI for pipeline progress, driven by event callbacks.

    Usage:
        progress = PipelineProgress()
        with progress:
            await run_loop(brief, config, on_event=progress.on_event)
    """

    def __init__(self) -> None:
        self._agent: str = "initializing"
        self._iteration: int = 0
        self._max_iterations: int = 1
        self._score: float = 0.0
        self._best_score: float = 0.0
        self._best_iteration: int = 0
        self._asset_count: int = 0
        self._total_assets: int = 0
        self._status: str = "starting"
        self._events: list[str] = []
        self._skills: list[str] = []

        # Rich components
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=30),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        )
        self._task_id = self._progress.add_task("Pipeline", total=100)
        self._live: Live | None = None

    def __enter__(self) -> PipelineProgress:
        self._live = Live(self._build_layout(), refresh_per_second=4)
        self._live.__enter__()
        return self

    def __exit__(self, *args: Any) -> None:
        if self._live:
            self._live.__exit__(*args)

    def on_event(self, event: str, data: dict[str, Any]) -> None:
        """Event callback for run_loop — updates the TUI state."""
        if event == "brief_loaded":
            self._status = "loaded"
            self._log(f"Brief: {data.get('task', '?')} ({data.get('style', 'default')})")

        elif event == "skills_discovered":
            skills = data.get("skills", [])
            self._skills = skills
            self._log(f"Skills: {', '.join(skills) if skills else 'none'}")

        elif event == "iteration_start":
            self._iteration = data.get("iteration", 0)
            self._max_iterations = data.get("max_iterations", 1)
            self._status = "running"
            self._agent = "memory"
            self._log(f"--- Iteration {self._iteration}/{self._max_iterations} ---")

        elif event == "iteration_complete":
            self._score = data.get("score", 0.0)
            self._best_score = data.get("best_score", 0.0)
            self._best_iteration = data.get("best_iteration", 0)
            self._asset_count = data.get("asset_count", 0)
            self._total_assets += self._asset_count
            passed = data.get("passed", False)
            icon = "PASS" if passed else "FAIL"
            self._log(
                f"Score: {self._score:.2f} [{icon}] | "
                f"Assets: {self._asset_count} | Best: {self._best_score:.2f}"
            )

        elif event == "iteration_timeout":
            self._log(f"Iteration {data.get('iteration', '?')} timed out")

        elif event == "loop_complete":
            self._status = "complete"
            total = data.get("total_iterations", 0)
            self._log(
                f"Complete! {total} iterations, "
                f"best score: {data.get('best_score', 0):.2f}, "
                f"{data.get('total_assets', 0)} assets"
            )

        # Update progress bar
        if self._max_iterations > 0:
            pct = (self._iteration / self._max_iterations) * 100
            self._progress.update(self._task_id, completed=pct, description=self._status)

        if self._live:
            self._live.update(self._build_layout())

    def _log(self, msg: str) -> None:
        """Append a log line (keep last 12)."""
        self._events.append(msg)
        if len(self._events) > 12:
            self._events = self._events[-12:]

    def _build_layout(self) -> Layout:
        """Build the Rich layout for the TUI."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )

        # Header
        layout["header"].update(
            Panel(self._progress, title="MuseLoop Pipeline", border_style="cyan")
        )

        # Body: scores + log side by side
        layout["body"].split_row(
            Layout(name="scores", ratio=1),
            Layout(name="log", ratio=2),
        )

        # Score panel
        score_table = Table.grid(padding=(0, 2))
        score_table.add_column(style="bold")
        score_table.add_column()
        score_table.add_row("Iteration", f"{self._iteration}/{self._max_iterations}")
        score_table.add_row("Score", f"{self._score:.2f}")
        score_table.add_row("Best", f"{self._best_score:.2f} (iter {self._best_iteration})")
        score_table.add_row("Assets", str(self._total_assets))
        score_table.add_row("Agent", self._agent)
        layout["scores"].update(Panel(score_table, title="Status", border_style="green"))

        # Log panel
        log_text = Text("\n".join(self._events[-10:]) if self._events else "(waiting...)")
        layout["log"].update(Panel(log_text, title="Events", border_style="blue"))

        # Footer
        if self._skills:
            skills_text = Text(" | ".join(self._skills), style="dim")
        else:
            skills_text = Text("(discovering skills...)", style="dim")
        layout["footer"].update(Panel(skills_text, title="Skills", border_style="dim"))

        return layout
