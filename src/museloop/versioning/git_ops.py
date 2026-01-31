"""Git operations for iteration versioning."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from museloop.utils.logging import get_logger

logger = get_logger(__name__)


class GitOps:
    """Manages git commits per iteration in the output directory."""

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._repo = None

    def init(self) -> None:
        """Initialize a git repo in the output directory if one doesn't exist."""
        try:
            import git

            git_dir = self.output_dir / ".git"
            if git_dir.exists():
                self._repo = git.Repo(self.output_dir)
                logger.info("git_repo_opened", path=str(self.output_dir))
            else:
                self._repo = git.Repo.init(self.output_dir)
                # Create initial commit
                self._repo.index.commit("MuseLoop: initialize output repository")
                logger.info("git_repo_initialized", path=str(self.output_dir))
        except ImportError:
            logger.warning("gitpython_not_installed", message="Git versioning disabled")
        except Exception as e:
            logger.warning("git_init_failed", error=str(e))

    def commit_iteration(self, iteration: int, assets: list[dict[str, Any]]) -> str | None:
        """Commit all changes for an iteration and tag it."""
        if self._repo is None:
            return None

        try:
            # Stage all new/modified files
            self._repo.git.add(A=True)

            # Check if there are changes to commit
            if not self._repo.is_dirty() and not self._repo.untracked_files:
                logger.info("git_nothing_to_commit", iteration=iteration)
                return None

            # Build commit message
            asset_count = len(assets)
            message = f"MuseLoop iteration {iteration}: {asset_count} asset(s) generated"

            commit = self._repo.index.commit(message)
            tag_name = f"iteration-{iteration:03d}"
            self._repo.create_tag(tag_name, message=message)

            logger.info(
                "git_committed",
                iteration=iteration,
                commit=str(commit),
                tag=tag_name,
            )
            return str(commit)
        except Exception as e:
            logger.warning("git_commit_failed", iteration=iteration, error=str(e))
            return None

    def tag(self, tag_name: str, message: str | None = None) -> None:
        """Create a git tag at the current HEAD."""
        if self._repo is None:
            return
        try:
            self._repo.create_tag(tag_name, message=message or tag_name)
            logger.info("git_tagged", tag=tag_name)
        except Exception as e:
            logger.warning("git_tag_failed", tag=tag_name, error=str(e))

    def get_history(self) -> list[dict[str, Any]]:
        """Return the git log as a list of dicts."""
        if self._repo is None:
            return []

        history = []
        try:
            for commit in self._repo.iter_commits():
                history.append({
                    "hash": str(commit),
                    "message": commit.message.strip(),
                    "date": commit.committed_datetime.isoformat(),
                    "author": str(commit.author),
                })
        except Exception as e:
            logger.warning("git_log_failed", error=str(e))

        return history
