from src.agent.chat_workflow import evaluate_completion, parse_workflow_state
from src.agent.run_authorization import AuthorizationTarget, RunAuthorization


def test_cancellation_workflow_builds_completion_and_follow_up():
    snapshot = """
uid=1_0 StaticText "A Customer Care Professional has now joined"
uid=1_1 StaticText "I'm completing your request to cancel your Card(s)."
uid=1_2 StaticText "Would you like to proceed with the Card Cancellation?"
uid=1_3 StaticText "Yes. I understand and consent."
uid=1_4 StaticText "Requested account has been invalidated successfully."
uid=1_5 StaticText "Once the credit will be applied, contact us."
uid=1_6 StaticText "We will transfer it in your bank account or arrange the check for you."
uid=1_7 StaticText "I understand and will contact support after the credit posts."
uid=1_8 StaticText "You will receive a confirmation email in 24-48 hours."
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
    checklist = state.checklist(authorization)
    assert checklist[0]["complete"] is True
    assert checklist[1]["deferred"] is True
    assert checklist[1]["complete"] is False
    assert evaluate_completion(state, authorization, fresh=True).state == "partial"
    assert state.follow_up_actions(authorization)[0]["type"] == "contact_support_after_credit_posts"


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


def test_completion_requires_fresh_target_scoped_evidence():
    authorization = RunAuthorization(
        targets=[
            AuthorizationTarget(
                key="target-a",
                display="synthetic card A",
                authorized_actions=["close_card"],
            ),
            AuthorizationTarget(
                key="target-b",
                display="synthetic card B",
                authorized_actions=["close_card"],
            ),
        ],
        user_authorized=True,
    )
    state = parse_workflow_state('uid=1_0 StaticText "Synthetic card A has been closed."')

    stale = evaluate_completion(state, authorization, fresh=False)
    fresh = evaluate_completion(state, authorization, fresh=True, snapshot_id="snapshot-2")

    assert stale.state == "unknown"
    assert fresh.state == "incomplete"
    assert fresh.satisfied is False
    assert fresh.items[0]["complete"] is True
    assert fresh.items[1]["complete"] is False


def test_refund_completion_does_not_broaden_allowed_methods():
    authorization = RunAuthorization(
        target_account="synthetic card",
        authorized_actions=["request_credit_refund"],
        refund_methods=["check"],
        user_authorized=True,
    )
    state = parse_workflow_state(
        'uid=1_0 StaticText "The credit balance for synthetic card was transferred '
        'to your bank account."'
    )

    evaluation = evaluate_completion(state, authorization, fresh=True)

    assert evaluation.state == "incomplete"
    assert evaluation.items[0]["methods"] == []


def test_deferred_disposition_requires_acceptance_and_stays_partial():
    authorization = RunAuthorization(
        target_account="synthetic card",
        authorized_actions=["request_credit_refund"],
        user_authorized=True,
    )
    offered = parse_workflow_state(
        'uid=1_0 StaticText "Once the credit posts for synthetic card, contact us."'
    )
    accepted = parse_workflow_state(
        'uid=1_0 StaticText "Once the credit posts for synthetic card, contact us."\n'
        'uid=1_1 StaticText "I understand and will contact support after the credit posts."'
    )

    unresolved = evaluate_completion(offered, authorization, fresh=True)
    evaluation = evaluate_completion(accepted, authorization, fresh=True)

    assert unresolved.state == "incomplete"
    assert unresolved.satisfied is False
    assert evaluation.state == "partial"
    assert evaluation.satisfied is True
    assert evaluation.follow_up_actions[0]["status"] == "pending"
