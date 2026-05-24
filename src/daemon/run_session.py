"""Reconnectable run-session state for the helper daemon."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from src.agent.evidence import result_ready_payload
from src.agent.human_work import event_has_active_human_work
from src.agent.result import TaskResult


class RunStatus(StrEnum):
    """Reconnectable run states exposed by the helper."""

    PREPARING = "preparing"
    READY_TO_START = "ready_to_start"
    RUNNING = "running"
    WAITING_ON_USER = "waiting_on_user"
    WAITING_ON_REP = "waiting_on_rep"
    WAITING_ON_LOGIN = "waiting_on_login"
    WAITING_ON_AUTH = "waiting_on_auth"
    CHECKPOINT_PENDING = "checkpoint_pending"
    RECOVERY_PENDING = "recovery_pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunEventType(StrEnum):
    """Structured dashboard/helper protocol event types."""

    DECISION_CHECKPOINT = "decision_checkpoint"
    MISSING_INFORMATION = "missing_information"
    OTP_REQUIRED = "otp_required"
    AUTH_REQUIRED = "auth_required"
    MANUAL_LOGIN_REQUIRED = "manual_login_required"
    ACCOUNT_ACCESS_BLOCKED = "account_access_blocked"
    RESUME_AFTER_AUTH = "resume_after_auth"
    ATTACHMENT_REQUIRED = "attachment_required"
    ACTIVE_HUMAN_WORK = "active_human_work"
    IRREVERSIBLE_ACTION_PENDING = "irreversible_action_pending"
    OFFER_RECEIVED = "offer_received"
    RECOVERY_PENDING = "recovery_pending"
    RESULT_READY = "result_ready"


AUTH_EVENT_STATES = {
    RunEventType.MANUAL_LOGIN_REQUIRED: RunStatus.WAITING_ON_LOGIN,
    RunEventType.OTP_REQUIRED: RunStatus.WAITING_ON_AUTH,
    RunEventType.AUTH_REQUIRED: RunStatus.WAITING_ON_AUTH,
    RunEventType.ACCOUNT_ACCESS_BLOCKED: RunStatus.WAITING_ON_AUTH,
    RunEventType.RESUME_AFTER_AUTH: RunStatus.WAITING_ON_AUTH,
}

class RunStateStore:
    """Owns the reconnectable state snapshot for one active helper run."""

    def __init__(self):
        self.state: dict = {
            "type": "state",
            "status": RunStatus.READY_TO_START.value,
            "running": False,
            "needs_input": False,
            "site": None,
            "message": "Ready to start a supervised customer-service task.",
            "step": None,
            "updated_at": None,
            "started_at": None,
            "finished_at": None,
            "transcript": None,
            "result": None,
            "pending_request": None,
            "permission_mode": "supervised_browser",
            "preflight_failures": [],
            "timing_spans": [],
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


def timing_span(
    name: str,
    label: str,
    *,
    duration_ms: float,
    status: str = "ok",
    metadata: dict | None = None,
) -> dict:
    """Build a PII-free helper timing span for dashboard and evidence payloads."""
    return {
        "type": "timing_span",
        "name": name,
        "label": label,
        "duration_ms": round(max(duration_ms, 0.0), 1),
        "status": status,
        "timestamp": now_iso(),
        "metadata": metadata or {},
    }


def request_message(request: dict | None) -> str | None:
    if not request:
        return None
    if request.get("type") == "question":
        return request.get("question")
    if request.get("question"):
        return request.get("question")
    if request.get("type") == "decision_checkpoint":
        return request.get("checkpoint", {}).get("summary")
    if request.get("summary"):
        return request.get("summary")
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
        return "Checking the page and support chat before acting."
    return "Working on the customer-service chat."


def _is_generic_step_message(message: str) -> bool:
    return message.startswith("Step ") and (
        message.endswith(" started") or message.endswith(" complete")
    )


def protocol_event_for_request(request: dict) -> dict:
    return normalize_attention_request(request)


def normalize_attention_request(request: dict | None) -> dict | None:
    """Return a structured, reconnect-safe user-attention event envelope."""
    if not request:
        return None

    if request.get("type") == RunEventType.DECISION_CHECKPOINT.value:
        checkpoint = request.get("checkpoint") or {}
        event_type = _checkpoint_event_type(checkpoint)
        return {
            "type": event_type.value,
            "original_type": RunEventType.DECISION_CHECKPOINT.value,
            "checkpoint": checkpoint,
            "summary": checkpoint.get("summary"),
            "requires_user": True,
        }

    question = str(request.get("question") or "").strip()
    reason = str(request.get("reason") or "").strip()
    event_type = classify_user_attention(question=question, reason=reason)
    return {
        "type": event_type.value,
        "original_type": request.get("type") or "question",
        "question": question,
        "reason": reason,
        "requires_user": True,
    }


def classify_user_attention(*, question: str, reason: str) -> RunEventType:
    """Classify generic ask_user prompts into explicit protocol events."""
    text = f"{question} {reason}".lower()
    if any(
        marker in text
        for marker in ("otp", "mfa", "2fa", "verification code", "one-time code")
    ):
        return RunEventType.OTP_REQUIRED
    if any(
        marker in text
        for marker in ("blocked", "locked", "suspended", "access denied", "captcha")
    ):
        return RunEventType.ACCOUNT_ACCESS_BLOCKED
    if any(marker in text for marker in ("log in", "login", "sign in", "signin")):
        return RunEventType.MANUAL_LOGIN_REQUIRED
    if any(
        marker in text
        for marker in (
            "authenticate",
            "authentication",
            "verify your identity",
            "verification",
        )
    ):
        return RunEventType.AUTH_REQUIRED
    if any(
        marker in text
        for marker in ("upload", "attach", "attachment", "document", "screenshot", "pdf")
    ):
        return RunEventType.ATTACHMENT_REQUIRED
    if any(
        marker in text
        for marker in ("logged in", "sign-in complete", "resume", "continue after")
    ):
        return RunEventType.RESUME_AFTER_AUTH
    return RunEventType.MISSING_INFORMATION


def run_status_for_attention(request: dict | None) -> RunStatus:
    event_type = RunEventType((request or {}).get("type", RunEventType.MISSING_INFORMATION))
    if event_type == RunEventType.DECISION_CHECKPOINT:
        return RunStatus.CHECKPOINT_PENDING
    if event_type == RunEventType.IRREVERSIBLE_ACTION_PENDING:
        return RunStatus.CHECKPOINT_PENDING
    if event_type == RunEventType.OFFER_RECEIVED:
        return RunStatus.CHECKPOINT_PENDING
    if event_type == RunEventType.RECOVERY_PENDING:
        return RunStatus.RECOVERY_PENDING
    if event_type in AUTH_EVENT_STATES:
        return AUTH_EVENT_STATES[event_type]
    return RunStatus.WAITING_ON_USER


def progress_event_type(event: dict) -> RunEventType | None:
    if event_has_active_human_work(event):
        return RunEventType.ACTIVE_HUMAN_WORK
    return None


def _checkpoint_event_type(checkpoint: dict) -> RunEventType:
    checkpoint_type = checkpoint.get("type")
    if checkpoint_type == "irreversible_action":
        return RunEventType.IRREVERSIBLE_ACTION_PENDING
    if checkpoint_type == "offer_choice":
        return RunEventType.OFFER_RECEIVED
    if checkpoint_type == "timeout_risk":
        return RunEventType.RECOVERY_PENDING
    return RunEventType.DECISION_CHECKPOINT


def result_payload(result: TaskResult) -> dict:
    return result_ready_payload(result)
