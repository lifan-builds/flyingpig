from src.agent.chat_workflow import parse_workflow_state
from src.agent.run_authorization import RunAuthorization


def test_cancellation_workflow_builds_completion_and_follow_up():
    snapshot = """
uid=1_0 StaticText "A Customer Care Professional has now joined"
uid=1_1 StaticText "I'm completing your request to cancel your Card(s)."
uid=1_2 StaticText "Would you like to proceed with the Card Cancellation?"
uid=1_3 StaticText "Yes. I understand and consent."
uid=1_4 StaticText "Requested account has been invalidated successfully."
uid=1_5 StaticText "Once the credit will be applied, contact us."
uid=1_6 StaticText "We will transfer it in your bank account or arrange the check for you."
uid=1_7 StaticText "You will receive a confirmation email in 24-48 hours."
"""
    authorization = RunAuthorization(
        target_account="12345",
        authorized_actions=["close_card", "request_credit_refund"],
        refund_methods=["existing_checking", "check"],
        user_authorized=True,
    )

    state = parse_workflow_state(snapshot)

    assert state.stage == "closure_confirmed"
    assert state.confirmation_expected is True
    assert state.refund_methods_confirmed == ["existing_checking", "check"]
    assert all(item["complete"] for item in state.checklist(authorization))
    assert state.follow_up_actions()[0]["type"] == "contact_support_after_credit_posts"


def test_cancellation_workflow_detects_pending_consent():
    state = parse_workflow_state(
        'uid=1_0 StaticText "Would you like to proceed with the Card Cancellation?"'
    )

    assert state.stage == "consent_required"
    assert state.consent_sent is False


def test_new_consent_request_after_old_consent_is_pending_again():
    state = parse_workflow_state(
        """
uid=1_0 StaticText "Would you like to proceed with the Card Cancellation?"
uid=1_1 StaticText "Yes. I understand and consent."
uid=1_2 StaticText "A Customer Care Professional has now joined"
uid=1_3 StaticText "Would you like to proceed with the Card Cancellation?"
"""
    )

    assert state.stage == "consent_required"
