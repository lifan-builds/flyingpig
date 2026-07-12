"""Evidence capture and result extraction for agent runs."""

import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from browser_use.agent.views import AgentHistoryList

from src.agent.result import TaskResult, TaskStatus
from src.sites.base import BaseSiteAdapter

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SessionArtifacts:
    transcript_path: str
    chat_transcript: list[str]
    checkpoint_events: list[dict]
    result: TaskResult


class EvidenceRecorder:
    """Captures run artifacts and converts browser-use history into TaskResult."""

    def __init__(self, site_adapter: BaseSiteAdapter):
        self.site_adapter = site_adapter

    def save_session(
        self,
        history: AgentHistoryList,
        save_dir: Path,
        events: list[dict] | None = None,
    ) -> str:
        """Save the full session history to disk."""
        save_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        site_name = self.site_adapter.name.lower().replace(" ", "_")
        filename = f"session_{site_name}_{timestamp}.json"
        filepath = save_dir / filename

        history.save_to_file(str(filepath))
        if events:
            events_path = save_dir / f"session_{site_name}_{timestamp}_events.json"
            events_path.write_text(json.dumps(events, indent=2), encoding="utf-8")
            logger.info("Session events saved to %s", events_path)
        logger.info("Session saved to %s", filepath)
        return str(filepath)

    async def capture_chat_transcript(self, browser_session) -> list[str]:
        """Best-effort extraction of visible chat messages from the current page."""
        page = await browser_session.get_current_page()
        if page is None:
            return []

        raw = await page.evaluate(
            """() => {
                const selectors = [
                    '#chat-history',
                    '[data-testid*="chat" i]',
                    '[aria-label*="chat" i]',
                    '[class*="chat" i]',
                    '[id*="chat" i]',
                    'main',
                    'body'
                ];
                const seen = new Set();
                const lines = [];
                for (const selector of selectors) {
                    for (const node of document.querySelectorAll(selector)) {
                        const text = (node.innerText || node.textContent || '').trim();
                        if (!text) continue;
                        for (const line of text.split(/\\n+/)) {
                            const normalized = line.trim().replace(/\\s+/g, ' ');
                            if (normalized && !seen.has(normalized)) {
                                seen.add(normalized);
                                lines.push(normalized);
                            }
                        }
                    }
                }
                return lines;
            }"""
        )
        if isinstance(raw, list):
            parsed = raw
        else:
            try:
                parsed = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return [raw] if isinstance(raw, str) and raw else []
        return [line for line in parsed if isinstance(line, str)]

    def extract_chat_transcript_from_history(self, history: AgentHistoryList) -> list[str]:
        """Extract chat-looking lines from browser-use state snapshots."""
        seen: set[str] = set()
        lines: list[str] = []
        for item in history.history:
            state_message = getattr(item, "state_message", "") or ""
            for match in re.finditer(
                r"<browser_state>(.*?)</browser_state>",
                state_message,
                flags=re.DOTALL,
            ):
                browser_state = match.group(1)
                for raw_line in browser_state.splitlines():
                    line = raw_line.strip()
                    if not line.startswith(("Agent:", "You:")):
                        continue
                    if line in seen:
                        continue
                    seen.add(line)
                    lines.append(line)
        return lines

    def extract_result(
        self,
        history: AgentHistoryList,
        chat_transcript: list[str] | None = None,
        checkpoint_events: list[dict] | None = None,
    ) -> TaskResult:
        """Extract a structured TaskResult from the agent's history."""
        chat_transcript = chat_transcript or []
        checkpoint_events = checkpoint_events or []
        final = history.final_result()
        steps = history.number_of_steps()
        duration = history.total_duration_seconds()

        if final and "[NEEDS_INPUT]" in final:
            return TaskResult(
                status=TaskStatus.NEEDS_INPUT,
                summary=final.replace("[NEEDS_INPUT] ", ""),
                transcript=history.agent_steps(),
                chat_transcript=chat_transcript,
                checkpoint_events=checkpoint_events,
                steps_taken=steps,
                duration_seconds=duration,
            )

        outcome_details = {}
        if final:
            try:
                outcome_details = json.loads(final)
            except (json.JSONDecodeError, TypeError):
                outcome_details = {"raw": final}

        agent_success = getattr(history, "is_successful", lambda: None)()
        if agent_success is False:
            status = TaskStatus.FAILED
        elif agent_success is True:
            status = TaskStatus.SUCCESS
        else:
            status = TaskStatus.SUCCESS if final else TaskStatus.PARTIAL

        return TaskResult(
            status=status,
            summary=outcome_details.get("outcome", final or "No result captured"),
            transcript=history.agent_steps(),
            chat_transcript=chat_transcript,
            checkpoint_events=checkpoint_events,
            steps_taken=steps,
            duration_seconds=duration,
            outcome_details=outcome_details,
        )

    async def record_session_result(
        self,
        *,
        history: AgentHistoryList,
        browser_session,
        save_dir: Path,
        checkpoint_events: list[dict],
    ) -> SessionArtifacts:
        """Capture chat evidence, save artifacts, and return the linked result."""
        chat_transcript = await self.capture_chat_transcript(browser_session)
        if not chat_transcript:
            chat_transcript = self.extract_chat_transcript_from_history(history)

        transcript_path = self.save_session(
            history,
            save_dir,
            events=checkpoint_events,
        )
        result = self.extract_result(
            history,
            chat_transcript=chat_transcript,
            checkpoint_events=checkpoint_events,
        )
        result.transcript_path = transcript_path
        return SessionArtifacts(
            transcript_path=transcript_path,
            chat_transcript=chat_transcript,
            checkpoint_events=checkpoint_events,
            result=result,
        )


def result_ready_payload(result: TaskResult) -> dict:
    """Build the event-shaped, evidence-linked final result payload."""
    status = str(result.status).split(".")[-1].lower()
    details = result.outcome_details or {}
    timing_summary = timing_summary_payload(result.timing_spans)
    checkpoint_decisions = [
        {
            "checkpoint_id": event.get("checkpoint_id") or event.get("expected_checkpoint_id"),
            "selected_option_id": event.get("selected_option_id"),
            "selected_message": event.get("selected_message"),
            "free_text": event.get("free_text"),
            "timestamp": event.get("timestamp"),
        }
        for event in result.checkpoint_events
        if event.get("event_type") == "decision_checkpoint_answered"
    ]
    unresolved_items = details.get("unresolved_items")
    if isinstance(unresolved_items, str):
        unresolved_items = [unresolved_items]
    elif not isinstance(unresolved_items, list):
        unresolved_items = []
    if details.get("next_steps"):
        unresolved_items.append(str(details["next_steps"]))
    scorecard = run_scorecard_payload(
        result,
        status=status,
        timing_summary=timing_summary,
        checkpoint_decisions_count=len(checkpoint_decisions),
        unresolved_items=unresolved_items,
    )

    return {
        "type": "result_ready",
        "status": status,
        "summary": result.summary,
        "outcome_summary": result.summary,
        "steps": result.steps_taken,
        "duration": result.duration_seconds,
        "transcript": str(result.transcript_path) if result.transcript_path else None,
        "evidence": {
            "transcript_path": str(result.transcript_path) if result.transcript_path else None,
            "chat_transcript_lines": len(result.chat_transcript),
            "checkpoint_events_count": len(result.checkpoint_events),
            "timing_spans_count": len(result.timing_spans),
        },
        "timing_spans": result.timing_spans,
        "timing_summary": timing_summary,
        "human_reached": details.get("human_reached"),
        "offer_result": details.get("amount_saved")
        or details.get("offer")
        or details.get("result")
        or details.get("confirmation_number"),
        "unresolved_items": unresolved_items,
        "completion_checklist": details.get("completion_checklist") or [],
        "follow_up_actions": details.get("follow_up_actions") or [],
        "confirmation_expected": details.get("confirmation_expected"),
        "time_saved": details.get("time_saved"),
        "checkpoint_decisions": checkpoint_decisions,
        "checkpoint_events_count": len(result.checkpoint_events),
        "scorecard": scorecard,
    }


def timing_summary_payload(spans: list[dict]) -> dict:
    """Return a compact timing summary with no chat content or PII."""
    totals: dict[str, float] = {}
    for span in spans:
        name = str(span.get("name") or "unknown")
        duration = float(span.get("duration_ms") or 0.0)
        totals[name] = round(totals.get(name, 0.0) + duration, 1)
    return {
        "total_ms": round(sum(totals.values()), 1),
        "span_count": len(spans),
        "by_name_ms": totals,
    }


def run_scorecard_payload(
    result: TaskResult,
    *,
    status: str | None = None,
    timing_summary: dict | None = None,
    checkpoint_decisions_count: int | None = None,
    unresolved_items: list[str] | None = None,
) -> dict:
    """Return a PII-free beta outcome scorecard for local product measurement."""
    details = result.outcome_details or {}
    status_value = status or str(result.status).split(".")[-1].lower()
    timing = timing_summary or timing_summary_payload(result.timing_spans)
    checkpoint_count = (
        checkpoint_decisions_count
        if checkpoint_decisions_count is not None
        else sum(
            1
            for event in result.checkpoint_events
            if event.get("event_type") == "decision_checkpoint_answered"
        )
    )
    question_count = sum(
        1 for event in result.checkpoint_events if event.get("event_type") == "question_answered"
    )
    unresolved = unresolved_items if unresolved_items is not None else []
    blocked_reason = (
        details.get("blocked_reason")
        or details.get("failure_reason")
        or details.get("error")
        or (
            "Run failed before a structured reason was captured."
            if status_value == "failed"
            else None
        )
    )

    return {
        "schema_version": 1,
        "goal_type": details.get("goal_type") or details.get("template") or "automatic",
        "site_profile": details.get("site_profile") or details.get("site"),
        "final_status": status_value,
        "human_reached": details.get("human_reached"),
        "huca_attempts": int(details.get("huca_attempts") or 0),
        "checkpoint_count": checkpoint_count,
        "user_intervention_count": checkpoint_count + question_count,
        "duration_seconds": result.duration_seconds,
        "timing_total_ms": timing.get("total_ms", 0.0),
        "offer_result": details.get("amount_saved")
        or details.get("offer")
        or details.get("result")
        or details.get("confirmation_number"),
        "blocked_reason": blocked_reason,
        "unresolved_items_count": len(unresolved),
        "user_confirmed_outcome": details.get("user_confirmed_outcome"),
    }
