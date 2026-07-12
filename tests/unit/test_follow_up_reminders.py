from datetime import UTC, datetime, timedelta

from src.daemon.follow_up_reminders import FollowUpReminderStore


def test_reminders_persist_and_claim_once(tmp_path):
    path = tmp_path / "reminders.json"
    store = FollowUpReminderStore(path)
    due_at = datetime.now(UTC) - timedelta(minutes=1)

    created = store.create(
        title="Contact support",
        message="Request the remaining credit balance.",
        due_at=due_at,
        source={"type": "contact_support_after_credit_posts"},
    )

    reloaded = FollowUpReminderStore(path)
    assert reloaded.list()[0].id == created.id
    assert reloaded.claim_due()[0].status == "delivered"
    assert reloaded.claim_due() == []


def test_pending_reminder_can_be_cancelled(tmp_path):
    store = FollowUpReminderStore(tmp_path / "reminders.json")
    reminder = store.create(
        title="Contact support",
        message="Follow up.",
        due_at=datetime.now(UTC) + timedelta(days=1),
    )

    cancelled = store.cancel(reminder.id)

    assert cancelled is not None
    assert cancelled.status == "cancelled"
    assert store.claim_due(datetime.now(UTC) + timedelta(days=2)) == []
