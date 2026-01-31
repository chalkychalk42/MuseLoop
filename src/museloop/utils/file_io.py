"""Asset path management and file I/O utilities."""

from __future__ import annotations

from pathlib import Path


def ensure_dir(path: str | Path) -> Path:
    """Ensure a directory exists, creating it if necessary."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def iteration_dir(output_dir: str | Path, iteration: int) -> Path:
    """Get the directory for a specific iteration's assets."""
    path = Path(output_dir) / f"iteration-{iteration:03d}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def asset_path(output_dir: str | Path, iteration: int, name: str, ext: str) -> Path:
    """Generate a path for a named asset in an iteration directory."""
    idir = iteration_dir(output_dir, iteration)
    return idir / f"{name}.{ext.lstrip('.')}"
