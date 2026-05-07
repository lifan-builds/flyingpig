"""Evidence capture and result extraction for agent runs."""

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path

from browser_use.agent.views import AgentHistoryList

from src.agent.result import TaskResult, TaskStatus
from src.sites.base import BaseSiteAdapter

logger = logging.getLogger(__name__)


class EvidenceRecorder:
    """Captures run artifacts and converts browser-use history into TaskResult."""

    def __init__(self, site_adapter: BaseSiteAdapter):
        self.site_adapter = site_adapter

    def save_session(self, history: AgentHistoryList, save_dir: Path) -> str:
        """Save the full session history to disk."""
        save_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        site_name = self.site_adapter.name.lower().replace(" ", "_")
        filename = f"session_{site_name}_{timestamp}.json"
        filepath = save_dir / filename

        history.save_to_file(str(filepath))
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
    ) -> TaskResult:
        """Extract a structured TaskResult from the agent's history."""
        chat_transcript = chat_transcript or []
        final = history.final_result()
        steps = history.number_of_steps()
        duration = history.total_duration_seconds()

        if final and "[NEEDS_INPUT]" in final:
            return TaskResult(
                status=TaskStatus.NEEDS_INPUT,
                summary=final.replace("[NEEDS_INPUT] ", ""),
                transcript=history.agent_steps(),
                chat_transcript=chat_transcript,
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
            steps_taken=steps,
            duration_seconds=duration,
            outcome_details=outcome_details,
        )
