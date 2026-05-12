from src.agent.result import TaskResult, TaskStatus
from src.daemon.run_session import (
    RunStateStore,
    protocol_event_for_request,
    request_message,
    result_payload,
)


def test_run_state_store_applies_timestamped_reconnect_snapshot():
    store = RunStateStore()

    snapshot = store.apply(
        status="needs_input",
        running=True,
        needs_input=True,
        pending_request={"type": "question", "question": "Confirm?", "reason": "test"},
    )

    assert snapshot["type"] == "state"
    assert snapshot["status"] == "needs_input"
    assert snapshot["updated_at"]
    assert store.snapshot()["pending_request"]["question"] == "Confirm?"


def test_protocol_event_for_decision_checkpoint_request():
    request = {
        "type": "decision_checkpoint",
        "checkpoint": {"checkpoint_id": "cp_test", "summary": "Choose next step."},
    }

    assert request_message(request) == "Choose next step."
    assert protocol_event_for_request(request) == {
        "type": "decision_checkpoint",
        "checkpoint": request["checkpoint"],
    }


def test_result_payload_includes_checkpoint_audit_count():
    payload = result_payload(
        TaskResult(
            status=TaskStatus.SUCCESS,
            summary="Done",
            checkpoint_events=[{"event_type": "decision_checkpoint_answered"}],
            steps_taken=2,
            duration_seconds=3.5,
        )
    )

    assert payload["status"] == "success"
    assert payload["checkpoint_events_count"] == 1
