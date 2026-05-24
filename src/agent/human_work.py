"""Customer-service human wait and handoff semantics.

This module owns the phrases and guards that distinguish Active Human Work
from a dead chat or a completed result. Keep these rules shared between the
agent tools and daemon run-state protocol so user-facing wait states agree
with stale-result prevention.
"""

from __future__ import annotations

import re

MISSING_DOCUMENTATION_MARKERS = (
    "no reference",
    "no separate reference",
    "no confirmation",
    "no reference number",
    "no reference/timing",
    "not provided",
    "was not provided",
    "were not provided",
)

PENDING_HUMAN_WORK_MARKERS = (
    "allow me one moment",
    "allow me a moment",
    "one moment please",
    "give me a moment",
    "please wait",
    "still checking",
    "still reviewing",
    "i am checking",
    "i'm checking",
    "checking some details",
    "let me check",
    "let me see",
    "bear with me",
    "reviewing this",
    "working on this",
)

PENDING_HANDOFF_MARKERS = (
    "i'll connect you",
    "i will connect you",
    "connect you with",
    "connect you to",
    "transfer you to",
    "transfer you with",
    "connecting you",
    "member care team now",
    "live agent",
    "live representative",
    "human representative",
)

PENDING_HANDOFF_OUTCOME_MARKERS = (
    "pending transfer",
    "pending handoff",
    "still pending",
    "awaiting transfer",
    "waiting for transfer",
    "no verified final confirmation",
    "do not have a verified final confirmation",
    "no human-provided final answer",
)


def outcome_claims_missing_documentation(details: dict) -> bool:
    """Return true when a final outcome claims missing reference/timing details."""
    text = " ".join(str(value or "") for value in details.values()).lower()
    return any(marker in text for marker in MISSING_DOCUMENTATION_MARKERS)


def outcome_claims_pending_handoff(details: dict) -> bool:
    """Return true when a final outcome says a support transfer is unresolved."""
    text = " ".join(str(value or "") for value in details.values()).lower()
    return any(marker in text for marker in PENDING_HANDOFF_OUTCOME_MARKERS)


def text_has_pending_human_work(text: str) -> bool:
    """Detect visible chat text that suggests a human rep is actively working."""
    tail = text.lower()[-2000:]
    return any(marker in tail for marker in PENDING_HUMAN_WORK_MARKERS)


def text_has_pending_support_handoff(text: str) -> bool:
    """Detect visible chat text that suggests a human support transfer is pending."""
    tail = text.lower()[-2500:]
    return any(marker in tail for marker in PENDING_HANDOFF_MARKERS)


def event_has_active_human_work(event: dict) -> bool:
    """Return true when a daemon progress event describes Active Human Work."""
    text = " ".join(
        str(event.get(key) or "")
        for key in ("message", "goal", "thought", "display_message")
    ).lower()
    return any(marker in text for marker in PENDING_HUMAN_WORK_MARKERS)


def find_reference_numbers(text: str) -> list[str]:
    """Extract likely customer-service reference or confirmation numbers."""
    matches = re.findall(
        r"(?:reference|confirmation|case|ticket|records?\s+is|records?\s+are)"
        r"[^#\d]{0,80}(#?\d{5,12})",
        text,
        flags=re.IGNORECASE,
    )
    hash_matches = re.findall(r"#\d{5,12}\b", text)
    seen: set[str] = set()
    refs: list[str] = []
    for match in [*matches, *hash_matches]:
        ref = match if match.startswith("#") else f"#{match}"
        if ref not in seen:
            seen.add(ref)
            refs.append(ref)
    return refs
