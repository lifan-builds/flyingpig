from src.agent.human_work import (
    event_has_active_human_work,
    find_reference_numbers,
    outcome_claims_missing_documentation,
    text_has_pending_human_work,
    text_has_pending_support_handoff,
)


def test_active_human_work_module_classifies_wait_and_handoff_language():
    assert text_has_pending_human_work("Thanks. Allow me one moment while I review.")
    assert event_has_active_human_work({"display_message": "Rep is working on this now."})
    assert text_has_pending_support_handoff("I will connect you with a live representative.")


def test_active_human_work_module_supports_stale_outcome_guard_inputs():
    assert outcome_claims_missing_documentation({"next_steps": "No reference was provided."})
    assert find_reference_numbers("Your confirmation number is 1234567.") == ["#1234567"]
