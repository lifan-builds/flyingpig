"""Transcript-derived workflow state for customer-service conversations."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.agent.run_authorization import RunAuthorization

STATIC_TEXT_RE = re.compile(r'(?:StaticText|text) "(.*)"$')


@dataclass(frozen=True)
class ChatWorkflowState:
    """Small, generic state summary derived from the visible chat transcript."""

    messages: list[str] = field(default_factory=list)
    human_reached: bool = False
    human_active: bool = False
    active_human_message: str | None = None
    disclosure_presented: bool = False
    consent_requested: bool = False
    consent_sent: bool = False
    closure_confirmed: bool = False
    confirmation_expected: bool = False
    refund_follow_up_required: bool = False
    refund_methods_confirmed: list[str] = field(default_factory=list)
    representative_left: bool = False

    @property
    def stage(self) -> str:
        if self.closure_confirmed:
            return "closure_confirmed"
        if self.consent_requested and not self.consent_sent:
            return "consent_required"
        if self.disclosure_presented:
            return "disclosure"
        if self.human_active:
            return "human_active"
        if self.human_reached:
            return "human_reached"
        return "initial"

    def checklist(self, authorization: RunAuthorization) -> list[dict]:
        """Return goal completion items appropriate to the authorization."""
        items: list[dict] = []
        if authorization.permits("close_card"):
            items.append(
                {
                    "id": "close_card",
                    "complete": self.closure_confirmed,
                    "evidence": _last_matching(
                        self.messages,
                        "invalidated successfully",
                        "submitted for cancellation",
                        "card has been closed",
                    ),
                }
            )
        if authorization.permits("request_credit_refund"):
            complete = bool(self.refund_methods_confirmed) or self.refund_follow_up_required
            items.append(
                {
                    "id": "credit_refund_disposition",
                    "complete": complete,
                    "deferred": self.refund_follow_up_required,
                    "methods": self.refund_methods_confirmed,
                    "evidence": _last_matching(
                        self.messages,
                        "transfer it in your bank account",
                        "arrange the check",
                        "credit balance",
                    ),
                }
            )
        return items

    def follow_up_actions(self) -> list[dict]:
        """Return deferred actions discovered from the transcript."""
        if not self.refund_follow_up_required:
            return []
        return [
            {
                "type": "contact_support_after_credit_posts",
                "status": "pending",
                "methods": self.refund_methods_confirmed or ["existing_checking", "check"],
            }
        ]


def parse_workflow_state(snapshot_text: str) -> ChatWorkflowState:
    """Extract transcript messages and derive workflow signals."""
    messages: list[str] = []
    for raw_line in snapshot_text.splitlines():
        match = STATIC_TEXT_RE.search(raw_line.strip())
        if not match:
            continue
        text = match.group(1).replace('\\"', '"').strip()
        if text and (not messages or messages[-1] != text):
            messages.append(text)
    joined = "\n".join(messages).lower()
    refund_methods = []
    if "bank account" in joined or "checking account" in joined:
        refund_methods.append("existing_checking")
    if "arrange the check" in joined or "by check" in joined:
        refund_methods.append("check")
    last_consent_request = _last_index_matching(
        messages,
        "would you like to proceed with the card cancellation",
        "please reply to confirm",
    )
    last_consent = _last_index_matching(
        messages,
        "i understand and consent",
        "yes. i understand and consent",
    )
    last_join = _last_index_matching(messages, "customer care professional has now joined")
    last_left = _last_index_matching(messages, "customer care professional has left")
    active_human_message = _last_matching(
        messages[-5:],
        "please allow me a minute",
        "give me a couple of minutes",
        "let me review",
        "let me check",
        "one moment",
    )
    return ChatWorkflowState(
        messages=messages,
        human_reached=(
            "customer care professional has now joined" in joined
            or "membership consulting" in joined
            or "you are now chatting with" in joined
        ),
        human_active=active_human_message is not None,
        active_human_message=active_human_message,
        disclosure_presented="completing your request to cancel" in joined,
        consent_requested=last_consent_request >= 0 and last_consent_request > last_consent,
        consent_sent=last_consent >= 0 and last_consent > last_consent_request,
        closure_confirmed=(
            "invalidated successfully and submitted for cancellation" in joined
            or "invalidated successfully" in joined
            or "card has been closed" in joined
            or "cancellation has been completed" in joined
        ),
        confirmation_expected=(
            "confirmation email" in joined and ("24-48" in joined or "24–48" in joined)
        ),
        refund_follow_up_required=("once the credit" in joined and "contact us" in joined),
        refund_methods_confirmed=refund_methods,
        representative_left=last_left > last_join,
    )


def _last_matching(messages: list[str], *phrases: str) -> str | None:
    for message in reversed(messages):
        lowered = message.lower()
        if any(phrase in lowered for phrase in phrases):
            return message
    return None


def _last_index_matching(messages: list[str], *phrases: str) -> int:
    for index in range(len(messages) - 1, -1, -1):
        lowered = messages[index].lower()
        if any(phrase in lowered for phrase in phrases):
            return index
    return -1
