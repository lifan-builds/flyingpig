"""Helper-owned safety gate for starting supervised customer-service runs."""

from __future__ import annotations

from dataclasses import dataclass

from src.sites.registry import list_sites


@dataclass(frozen=True)
class PreflightResult:
    """Structured result from the run-start safety gate."""

    ok: bool
    failures: list[dict]


SUPPORTED_PERMISSION_MODES = {"supervised_browser"}
SUPPORTED_LOGIN_EXPECTATIONS = {
    "manual_visible_browser",
    "already_logged_in",
    "no_login_expected",
}
FORBIDDEN_SCOPE_MARKERS = (
    "make a phone call",
    "call support",
    "call them",
    "phone support",
    "send an email",
    "email support",
    "check my email",
    "log in for me",
    "use my password",
    "store my password",
    "save my password",
    "use my credentials",
    "store credentials",
)
IRREVERSIBLE_TASK_MARKERS = (
    "cancel",
    "close account",
    "close my account",
    "delete account",
    "terminate",
    "accept offer",
    "change plan",
)


def preflight_check(msg: dict, *, site: str | None) -> PreflightResult:
    """Validate helper-owned safety gates before browser-use can act externally."""
    failures: list[dict] = []
    task = str(msg.get("task") or "").strip()
    task_lower = task.lower()

    if not site or site not in list_sites():
        failures.append(
            {
                "code": "missing_site",
                "message": "Choose a supported customer-service site or work window.",
            }
        )
    if not task:
        failures.append(
            {
                "code": "missing_task",
                "message": "Describe the customer-service problem before starting.",
            }
        )
    if any(marker in task_lower for marker in FORBIDDEN_SCOPE_MARKERS):
        failures.append(
            {
                "code": "unsupported_scope",
                "message": (
                    "Flying Pig only handles supervised browser chat runs. "
                    "It cannot make phone calls, manage email, or receive/store credentials."
                ),
            }
        )
    if not bool(msg.get("user_authorized")):
        failures.append(
            {
                "code": "missing_user_authorization",
                "message": "Confirm that Flying Pig may work in the visible browser for this task.",
            }
        )
    if msg.get("permission_mode") not in SUPPORTED_PERMISSION_MODES:
        failures.append(
            {
                "code": "unsupported_permission_mode",
                "message": "Permission mode must be supervised_browser.",
            }
        )
    if msg.get("evidence_capture") is not True:
        failures.append(
            {
                "code": "evidence_required",
                "message": "Evidence capture must be enabled for an auditable run.",
            }
        )
    if not msg.get("cdp_url"):
        failures.append(
            {
                "code": "missing_work_window",
                "message": "Launch and connect the Controlled Chrome work window first.",
            }
        )
    if not (msg.get("target_url") or msg.get("url")):
        failures.append(
            {
                "code": "missing_target_url",
                "message": "Refresh the work window so Flying Pig knows which tab to supervise.",
            }
        )
    if msg.get("login_expectation") not in SUPPORTED_LOGIN_EXPECTATIONS:
        failures.append(
            {
                "code": "login_expectation_required",
                "message": (
                    "Login/auth handling must be explicit: manual visible browser login, "
                    "already logged in, or no login expected."
                ),
            }
        )
    if any(marker in task_lower for marker in IRREVERSIBLE_TASK_MARKERS) and not bool(
        msg.get("irreversible_actions_require_checkpoint")
    ):
        failures.append(
            {
                "code": "checkpoint_required",
                "message": "Irreversible customer-service actions require a Decision Checkpoint.",
            }
        )

    return PreflightResult(ok=not failures, failures=failures)


def task_with_success_criteria(task: str, success_criteria: str | None) -> str:
    """Append explicit done criteria to the agent task without changing prompts."""
    success_criteria = (success_criteria or "").strip()
    if not success_criteria:
        return task
    return f"{task}\n\nWhat counts as done:\n{success_criteria}"
