"""Tests for GitOps versioning."""

from __future__ import annotations

from pathlib import Path

import pytest

from museloop.versioning.git_ops import GitOps


@pytest.fixture
def git_ops(tmp_path):
    ops = GitOps(tmp_path / "repo")
    ops.init()
    return ops


def test_init_creates_repo(git_ops):
    assert git_ops._repo is not None
    assert (git_ops.output_dir / ".git").exists()


def test_init_idempotent(tmp_path):
    path = tmp_path / "repo"
    ops1 = GitOps(path)
    ops1.init()
    ops2 = GitOps(path)
    ops2.init()
    assert ops2._repo is not None


def test_commit_iteration(git_ops):
    # Create a file to commit
    (git_ops.output_dir / "test.txt").write_text("hello")
    assets = [{"type": "image", "path": "test.png"}]

    commit_hash = git_ops.commit_iteration(1, assets)
    assert commit_hash is not None

    # Check tag was created
    tags = [t.name for t in git_ops._repo.tags]
    assert "iteration-001" in tags


def test_commit_nothing_to_commit(git_ops):
    assets = [{"type": "image", "path": "test.png"}]
    result = git_ops.commit_iteration(1, assets)
    assert result is None


def test_tag(git_ops):
    # Create something to tag
    (git_ops.output_dir / "file.txt").write_text("data")
    git_ops._repo.git.add(A=True)
    git_ops._repo.index.commit("test commit")

    git_ops.tag("best-v1")
    tags = [t.name for t in git_ops._repo.tags]
    assert "best-v1" in tags


def test_get_history(git_ops):
    # Initial commit should exist from init
    history = git_ops.get_history()
    assert len(history) >= 1
    assert "hash" in history[0]
    assert "message" in history[0]
    assert "date" in history[0]


def test_get_history_multiple(git_ops):
    for i in range(3):
        (git_ops.output_dir / f"file_{i}.txt").write_text(f"content {i}")
        git_ops.commit_iteration(i + 1, [{"type": "test"}])

    history = git_ops.get_history()
    # Initial commit + 3 iterations
    assert len(history) == 4


def test_no_gitpython(tmp_path, monkeypatch):
    """GitOps should gracefully degrade if gitpython is missing."""
    ops = GitOps(tmp_path / "nogit")
    # Force repo to None (simulating import failure)
    ops._repo = None
    assert ops.commit_iteration(1, []) is None
    assert ops.get_history() == []
    ops.tag("test")  # Should not raise
