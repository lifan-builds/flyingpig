"""Reconnectable run-session state for the helper daemon."""

from __future__ import annotations

from datetime import UTC, datetime

from src.agent.result import TaskResult


class RunStateStore:
    """Owns the reconnectable state snapshot for one active helper run."""

    def __init__(self):
        self.state: dict = {
            "type": "state",
            "status": "idle",
            "running": False,
            "needs_input": False,
            "site": None,
            "message": "Idle",
            "step": None,
            "updated_at": None,
            "started_at": None,
            "finished_at": None,
            "transcript": None,
            "result": None,
            "pending_request": None,
        }

    def snapshot(self) -> dict:
        return dict(self.state)

    def apply(self, **changes) -> dict:
        self.state.update(changes)
        self.state["type"] = "state"
        self.state["updated_at"] = now_iso()
        return self.snapshot()


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def request_message(request: dict | None) -> str | None:
    if not request:
        return None
    if request.get("type") == "question":
        return request.get("question")
    if request.get("type") == "decision_checkpoint":
        return request.get("checkpoint", {}).get("summary")
    return None


def protocol_event_for_request(request: dict) -> dict:
    if request.get("type") == "decision_checkpoint":
        return {
            "type": "decision_checkpoint",
            "checkpoint": request.get("checkpoint"),
        }
    return {
        "type": "question",
        "question": request.get("question"),
        "reason": request.get("reason"),
    }


def result_payload(result: TaskResult) -> dict:
    status = str(result.status).split(".")[-1].lower()
    return {
        "type": "result",
        "status": status,
        "summary": result.summary,
        "steps": result.steps_taken,
        "duration": result.duration_seconds,
        "transcript": str(result.transcript_path) if result.transcript_path else None,
        "checkpoint_events_count": len(result.checkpoint_events),
    }
