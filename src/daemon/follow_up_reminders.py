"""Persistent local reminders for deferred customer-service follow-ups."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field


class FollowUpReminder(BaseModel):
    """One local reminder emitted by the helper when it becomes due."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    title: str
    message: str
    due_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: str = "pending"
    source: dict = Field(default_factory=dict)


class FollowUpReminderStore:
    """JSON-backed reminder store scoped to the local Flying Pig profile."""

    def __init__(self, path: Path | None = None):
        self.path = path or Path.home() / ".flyingpig" / "follow_up_reminders.json"

    def list(self) -> list[FollowUpReminder]:
        """Return reminders ordered by due time."""
        reminders = self._load()
        return sorted(reminders, key=lambda item: item.due_at)

    def create(
        self,
        *,
        title: str,
        message: str,
        due_at: datetime,
        source: dict | None = None,
    ) -> FollowUpReminder:
        """Persist a new pending reminder."""
        reminder = FollowUpReminder(
            title=title.strip(),
            message=message.strip(),
            due_at=_as_utc(due_at),
            source=source or {},
        )
        reminders = self._load()
        reminders.append(reminder)
        self._save(reminders)
        return reminder

    def cancel(self, reminder_id: str) -> FollowUpReminder | None:
        """Cancel a pending reminder by id."""
        reminders = self._load()
        updated = None
        for reminder in reminders:
            if reminder.id == reminder_id and reminder.status == "pending":
                reminder.status = "cancelled"
                updated = reminder
        if updated:
            self._save(reminders)
        return updated

    def claim_due(self, now: datetime | None = None) -> list[FollowUpReminder]:
        """Atomically mark due pending reminders as delivered and return them."""
        current = _as_utc(now or datetime.now(UTC))
        reminders = self._load()
        due = []
        for reminder in reminders:
            if reminder.status == "pending" and reminder.due_at <= current:
                reminder.status = "delivered"
                due.append(reminder)
        if due:
            self._save(reminders)
        return due

    def _load(self) -> list[FollowUpReminder]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return [FollowUpReminder.model_validate(item) for item in payload]
        except (OSError, ValueError, TypeError):
            return []

    def _save(self, reminders: list[FollowUpReminder]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                [item.model_dump(mode="json") for item in reminders],
                indent=2,
            ),
            encoding="utf-8",
        )
        temporary.replace(self.path)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
