from src.agent.result import TaskResult, TaskStatus
from src.daemon.run_session import (
    RunStateStore,
    RunStatus,
    classify_user_attention,
    progress_event_type,
    protocol_event_for_request,
    request_message,
    result_payload,
    run_status_for_attention,
)


def test_run_state_store_applies_timestamped_reconnect_snapshot():
    store = RunStateStore()

    snapshot = store.apply(
        status=RunStatus.WAITING_ON_USER.value,
        running=True,
        needs_input=True,
        pending_request={
            "type": "missing_information",
            "question": "Confirm?",
            "reason": "test",
        },
    )

    assert snapshot["type"] == "state"
    assert snapshot["status"] == "waiting_on_user"
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
        "original_type": "decision_checkpoint",
        "checkpoint": request["checkpoint"],
        "summary": "Choose next step.",
        "requires_user": True,
    }


def test_protocol_event_classifies_manual_login_and_otp():
    login = protocol_event_for_request(
        {
            "type": "question",
            "question": "Please log in in the visible browser.",
            "reason": "Site login is required.",
        }
    )
    otp = protocol_event_for_request(
        {
            "type": "question",
            "question": "Enter the one-time verification code.",
            "reason": "MFA verification.",
        }
    )

    assert login["type"] == "manual_login_required"
    assert run_status_for_attention(login).value == "waiting_on_login"
    assert otp["type"] == "otp_required"
    assert run_status_for_attention(otp).value == "waiting_on_auth"


def test_active_human_work_progress_event_is_detected():
    assert (
        progress_event_type(
            {"message": "The representative said please wait while they are checking."}
        )
        == "active_human_work"
    )
    classified = classify_user_attention(
        question="Please attach the invoice.",
        reason="needed",
    )
    assert classified.value == "attachment_required"


def test_result_ready_payload_is_evidence_linked():
    payload = result_payload(
        TaskResult(
            status=TaskStatus.SUCCESS,
            summary="Done",
            transcript_path="recordings/session.json",
            chat_transcript=["Agent: hello"],
            outcome_details={
                "human_reached": True,
                "amount_saved": "$25",
                "next_steps": "Credit posts in 5 days.",
                "completion_checklist": [{"id": "close_card", "complete": True}],
                "follow_up_actions": [
                    {"type": "contact_support_after_credit_posts", "status": "pending"}
                ],
                "confirmation_expected": True,
            },
            checkpoint_events=[
                {
                    "event_type": "decision_checkpoint_answered",
                    "checkpoint_id": "cp_1",
                    "selected_option_id": "accept",
                    "selected_message": "I accept.",
                }
            ],
            steps_taken=2,
            duration_seconds=3.5,
            timing_spans=[
                {
                    "type": "timing_span",
                    "name": "preflight",
                    "label": "Pre-flight safety gate",
                    "duration_ms": 12.5,
                    "status": "ok",
                }
            ],
        )
    )

    assert payload["type"] == "result_ready"
    assert payload["status"] == "success"
    assert payload["evidence"]["transcript_path"] == "recordings/session.json"
    assert payload["evidence"]["chat_transcript_lines"] == 1
    assert payload["human_reached"] is True
    assert payload["offer_result"] == "$25"
    assert payload["unresolved_items"] == ["Credit posts in 5 days."]
    assert payload["completion_checklist"][0]["complete"] is True
    assert payload["follow_up_actions"][0]["status"] == "pending"
    assert payload["confirmation_expected"] is True
    assert payload["checkpoint_decisions"][0]["selected_option_id"] == "accept"
    assert payload["checkpoint_events_count"] == 1
    assert payload["evidence"]["timing_spans_count"] == 1
    assert payload["timing_summary"]["by_name_ms"]["preflight"] == 12.5
    assert payload["scorecard"] == {
        "schema_version": 1,
        "goal_type": "automatic",
        "site_profile": None,
        "final_status": "success",
        "human_reached": True,
        "huca_attempts": 0,
        "checkpoint_count": 1,
        "user_intervention_count": 1,
        "duration_seconds": 3.5,
        "timing_total_ms": 12.5,
        "offer_result": "$25",
        "blocked_reason": None,
        "unresolved_items_count": 1,
        "user_confirmed_outcome": None,
    }
