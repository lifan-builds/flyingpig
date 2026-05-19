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


def progress_message(event: dict, request: dict | None = None) -> str:
    """Return dashboard-facing progress text for an agent event.

    browser-use emits useful `next_goal` text, but it can also emit generic
    "Step N started" noise. Keep the dashboard focused on what the agent is
    trying to do now, and let pending user-attention requests dominate.
    """
    pending_message = request_message(request)
    if pending_message:
        return pending_message

    for key in ("message", "goal", "thought"):
        raw = str(event.get(key) or "").strip()
        if raw and not _is_generic_step_message(raw):
            return raw
    if event.get("phase") == "starting":
        return "Checking the current page and chat state before the next action."
    return "Working on the customer-service chat."


def _is_generic_step_message(message: str) -> bool:
    return message.startswith("Step ") and (
        message.endswith(" started") or message.endswith(" complete")
    )


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
