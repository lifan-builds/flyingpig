"""Transcript-derived workflow state and fresh-evidence completion evaluation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from src.agent.run_authorization import AuthorizationTarget, RunAuthorization

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
    refund_follow_up_accepted: bool = False
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
        """Return target-scoped goal items appropriate to the authorization."""
        items: list[dict] = []
        for target in authorization.targets:
            if "close_card" in target.authorized_actions:
                evidence = _targeted_evidence(
                    self.messages,
                    target,
                    len(authorization.targets),
                    "invalidated successfully",
                    "submitted for cancellation",
                    "card has been closed",
                    "has been closed",
                    "cancellation has been completed",
                )
                items.append(
                    _checklist_item(
                        target=target,
                        action="close_card",
                        complete=self.closure_confirmed and evidence is not None,
                        evidence=evidence,
                        single_target=len(authorization.targets) == 1,
                    )
                )
            if "request_credit_refund" in target.authorized_actions:
                evidence = _targeted_evidence(
                    self.messages,
                    target,
                    len(authorization.targets),
                    "transfer it in your bank account",
                    "arrange the check",
                    "credit balance",
                    "once the credit",
                )
                deferred = self.refund_follow_up_required and evidence is not None
                acceptance = (
                    _targeted_evidence(
                        self.messages,
                        target,
                        len(authorization.targets),
                        "i understand",
                        "will contact support",
                        "contact support after",
                    )
                    if self.refund_follow_up_accepted
                    else None
                )
                confirmed_methods = [
                    method
                    for method in self.refund_methods_confirmed
                    if method in authorization.refund_methods
                ]
                complete = (
                    bool(confirmed_methods) and evidence is not None and not deferred
                )
                item = _checklist_item(
                    target=target,
                    action="credit_refund_disposition",
                    complete=complete,
                    deferred=deferred,
                    deferred_accepted=deferred and acceptance is not None,
                    evidence=evidence,
                    single_target=len(authorization.targets) == 1,
                )
                item["methods"] = confirmed_methods
                items.append(item)
        return items

    def follow_up_actions(self, authorization: RunAuthorization) -> list[dict]:
        """Return deferred actions without inventing an unapproved refund method."""
        if not self.refund_follow_up_required:
            return []
        confirmed = [
            method
            for method in self.refund_methods_confirmed
            if method in authorization.refund_methods
        ]
        return [
            {
                "type": "contact_support_after_credit_posts",
                "status": "pending",
                "methods": confirmed or list(authorization.refund_methods),
            }
        ]


@dataclass(frozen=True)
class CompletionEvaluation:
    """Deterministic outcome grounded in one explicitly fresh visible snapshot."""

    state: Literal["complete", "partial", "incomplete", "unknown"]
    satisfied: bool
    fresh: bool
    items: list[dict] = field(default_factory=list)
    unresolved_items: list[str] = field(default_factory=list)
    evidence_references: list[dict] = field(default_factory=list)
    follow_up_actions: list[dict] = field(default_factory=list)

    def outcome_details(self) -> dict:
        return {
            "completion_evaluation": self.state,
            "completion_checklist": self.items,
            "unresolved_items": self.unresolved_items,
            "evidence_references": self.evidence_references,
            "follow_up_actions": self.follow_up_actions,
        }


def evaluate_completion(
    workflow_state: ChatWorkflowState,
    authorization: RunAuthorization,
    *,
    fresh: bool,
    snapshot_id: str | None = None,
    accepted_deferred: set[str] | None = None,
) -> CompletionEvaluation:
    """Evaluate authorized goals without using task prose or stale observations."""
    if not fresh:
        return CompletionEvaluation(state="unknown", satisfied=False, fresh=False)

    items = workflow_state.checklist(authorization)
    if not items:
        return CompletionEvaluation(state="unknown", satisfied=False, fresh=True)

    accepted = accepted_deferred or set()
    normalized_items: list[dict] = []
    unresolved: list[str] = []
    evidence_references: list[dict] = []
    has_deferred = False
    for raw_item in items:
        item = dict(raw_item)
        item_key = f"{item.get('target_key')}:{item.get('action')}"
        deferred = bool(item.get("deferred"))
        deferred_accepted = deferred and (
            bool(item.get("deferred_accepted")) or item_key in accepted
        )
        item["deferred_accepted"] = deferred_accepted
        resolved = bool(item.get("complete")) or deferred_accepted
        item["resolved"] = resolved
        normalized_items.append(item)
        if not resolved:
            unresolved.append(str(item.get("id") or item_key))
        if deferred_accepted:
            has_deferred = True
        if item.get("evidence_reference"):
            reference = dict(item["evidence_reference"])
            if snapshot_id:
                reference["snapshot_id"] = snapshot_id
            evidence_references.append(reference)

    if unresolved:
        state: Literal["complete", "partial", "incomplete", "unknown"] = "incomplete"
        satisfied = False
    elif has_deferred:
        state = "partial"
        satisfied = True
    else:
        state = "complete"
        satisfied = True
    return CompletionEvaluation(
        state=state,
        satisfied=satisfied,
        fresh=True,
        items=normalized_items,
        unresolved_items=unresolved,
        evidence_references=evidence_references,
        follow_up_actions=workflow_state.follow_up_actions(authorization),
    )


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
    last_refund_deferred = _last_index_matching(messages, "once the credit")
    last_deferred_acceptance = _last_index_matching(
        messages,
        "i understand",
        "will contact support",
        "contact support after",
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
            or "has been closed" in joined
            or "cancellation has been completed" in joined
        ),
        confirmation_expected=(
            "confirmation email" in joined and ("24-48" in joined or "24–48" in joined)
        ),
        refund_follow_up_required=("once the credit" in joined and "contact us" in joined),
        refund_follow_up_accepted=(
            last_refund_deferred >= 0 and last_deferred_acceptance > last_refund_deferred
        ),
        refund_methods_confirmed=refund_methods,
        representative_left=last_left > last_join,
    )


def _checklist_item(
    *,
    target: AuthorizationTarget,
    action: str,
    complete: bool,
    evidence: tuple[int, str] | None,
    single_target: bool,
    deferred: bool = False,
    deferred_accepted: bool = False,
) -> dict:
    evidence_index = evidence[0] if evidence else None
    return {
        "id": action if single_target else f"{target.key}:{action}",
        "target_key": target.key,
        "action": action,
        "complete": complete,
        "deferred": deferred,
        "deferred_accepted": deferred_accepted,
        "evidence": evidence[1] if evidence else None,
        "evidence_reference": (
            {"kind": "visible_transcript_message", "message_index": evidence_index}
            if evidence_index is not None
            else None
        ),
    }


def _targeted_evidence(
    messages: list[str],
    target: AuthorizationTarget,
    target_count: int,
    *phrases: str,
) -> tuple[int, str] | None:
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        lowered = message.lower()
        if not any(phrase in lowered for phrase in phrases):
            continue
        if target_count == 1 or target.display.casefold() in message.casefold():
            return index, message
    return None


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
