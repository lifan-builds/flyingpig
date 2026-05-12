"""Task result types for customer-service runs."""

from dataclasses import dataclass, field
from enum import StrEnum


class TaskStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    NEEDS_INPUT = "needs_input"


@dataclass
class TaskResult:
    status: TaskStatus
    summary: str
    transcript: list[str] = field(default_factory=list)
    chat_transcript: list[str] = field(default_factory=list)
    checkpoint_events: list[dict] = field(default_factory=list)
    transcript_path: str | None = None
    outcome_details: dict = field(default_factory=dict)
    steps_taken: int = 0
    duration_seconds: float = 0.0
