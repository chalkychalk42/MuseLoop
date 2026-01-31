"""Job state tracking for background pipeline runs."""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Any


class JobStatus(str, enum.Enum):
    """Status of a pipeline job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    AWAITING_APPROVAL = "awaiting_approval"


@dataclass
class JobState:
    """Tracks the lifecycle of a single pipeline run."""

    job_id: str
    brief: dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    iteration: int = 0
    max_iterations: int = 5
    score: float = 0.0
    best_score: float = 0.0
    best_iteration: int = 0
    assets: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    output_dir: str | None = None
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None

    def add_event(self, event: str, data: dict[str, Any]) -> None:
        """Record a progress event."""
        self.events.append({"event": event, "data": data, "timestamp": time.time()})

    def to_summary(self) -> dict[str, Any]:
        """Return a JSON-serializable summary."""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "score": self.score,
            "best_score": self.best_score,
            "best_iteration": self.best_iteration,
            "asset_count": len(self.assets),
            "error": self.error,
            "output_dir": self.output_dir,
        }
