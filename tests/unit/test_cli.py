"""Tests for CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from museloop.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "MuseLoop v" in result.output


def test_inspect_brief(tmp_path):
    brief = {"task": "Test video", "style": "noir", "duration_seconds": 30}
    brief_path = tmp_path / "brief.json"
    brief_path.write_text(json.dumps(brief))

    result = runner.invoke(app, ["inspect", str(brief_path)])
    assert result.exit_code == 0
    assert "Test video" in result.output
    assert "noir" in result.output


def test_inspect_missing_brief():
    result = runner.invoke(app, ["inspect", "/nonexistent/brief.json"])
    assert result.exit_code == 1


def test_skills_list():
    result = runner.invoke(app, ["skills"])
    assert result.exit_code == 0
    # Should list available skills or show "No skills found"
    assert "Skills" in result.output or "No skills" in result.output


def test_skills_inspect_missing():
    result = runner.invoke(app, ["skills", "nonexistent_skill_xyz"])
    assert result.exit_code == 1


def test_dry_run(tmp_path):
    brief = {"task": "Dry run test", "style": "minimal"}
    brief_path = tmp_path / "brief.json"
    brief_path.write_text(json.dumps(brief))

    result = runner.invoke(app, ["run", str(brief_path), "--dry-run"])
    assert result.exit_code == 0
    assert "Dry run" in result.output
    assert "Dry run test" in result.output


def test_run_missing_brief():
    result = runner.invoke(app, ["run", "/nonexistent/brief.json"])
    assert result.exit_code == 1


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "MuseLoop" in result.output
