import asyncio
import json

import pytest
from pydantic import ValidationError
from src.agent import user_input as user_input_module
from src.agent.user_input import (
    DecisionCheckpointParams,
    DecisionOption,
    UserInputHandler,
    click_visible_control_tool,
    find_reference_numbers,
    outcome_claims_missing_documentation,
    outcome_claims_pending_handoff,
    text_has_pending_human_work,
    text_has_pending_support_handoff,
)


@pytest.mark.asyncio
async def test_decision_checkpoint_returns_selected_option_and_message():
    handler = UserInputHandler(mode="api")
    params = DecisionCheckpointParams(
        checkpoint_id="cp_test",
        type="strategy_pivot",
        summary="No retention offer is available.",
        recommended_option_id="close_card",
        options=[
            DecisionOption(
                id="close_card",
                label="Close card",
                consequence="Proceed to cancellation disclosure.",
                message_to_send="I would like to proceed toward closing the card.",
            ),
            DecisionOption(
                id="stop",
                label="Stop here",
                consequence="No account change is made.",
                message_to_send="Thanks, I will decide later.",
            ),
        ],
    )

    task = asyncio.create_task(handler.decision_checkpoint(params))
    await asyncio.sleep(0)

    assert handler.pending_request is not None
    assert handler.pending_request["type"] == "decision_checkpoint"

    handler.provide_input(
        json.dumps(
            {
                "checkpoint_id": "cp_test",
                "selected_option_id": "close_card",
                "selected_message": "I would like to proceed toward closing the card.",
            }
        )
    )
    response = json.loads(await task)

    assert response["checkpoint_id"] == "cp_test"
    assert response["selected_option_id"] == "close_card"
    assert response["selected_message"] == "I would like to proceed toward closing the card."
    assert handler.pending_request is None
    assert [event["event_type"] for event in handler.events] == [
        "decision_checkpoint_opened",
        "decision_checkpoint_answered",
    ]


@pytest.mark.asyncio
async def test_decision_checkpoint_holding_message_timeout():
    handler = UserInputHandler(mode="api")
    params = DecisionCheckpointParams(
        checkpoint_id="cp_hold",
        type="timeout_risk",
        summary="The rep is waiting for a user decision.",
        recommended_option_id="stop",
        options=[
            DecisionOption(
                id="stop",
                label="Stop here",
                consequence="No account change is made.",
                message_to_send="Thanks, I will decide later.",
            ),
        ],
        holding_message="Please give me a moment to review this.",
        holding_message_after_seconds=1,
    )

    response = json.loads(await handler.decision_checkpoint(params))

    assert response["selected_option_id"] == "__holding_message__"
    assert response["selected_message"] == "Please give me a moment to review this."
    assert response["is_holding_message"] is True
    assert handler.pending_request is None
    assert handler.events[-1]["event_type"] == "decision_checkpoint_holding_message"


def test_decision_checkpoint_requires_recommended_option_to_exist():
    with pytest.raises(ValidationError):
        DecisionCheckpointParams(
            checkpoint_id="cp_invalid",
            type="strategy_pivot",
            summary="No retention offer is available.",
            recommended_option_id="missing",
            options=[
                DecisionOption(
                    id="stop",
                    label="Stop here",
                    consequence="No account change is made.",
                    message_to_send="Thanks, I will decide later.",
                ),
            ],
        )


def test_irreversible_decision_checkpoint_requires_exact_messages():
    with pytest.raises(ValidationError):
        DecisionCheckpointParams(
            checkpoint_id="cp_irreversible",
            type="irreversible_action",
            summary="Amex is asking for final cancellation approval.",
            recommended_option_id="approve",
            options=[
                DecisionOption(
                    id="approve",
                    label="Approve closure",
                    consequence="The card will be closed.",
                ),
            ],
        )


def test_decision_checkpoint_requires_complete_holding_message_pair():
    with pytest.raises(ValidationError):
        DecisionCheckpointParams(
            checkpoint_id="cp_hold_invalid",
            type="timeout_risk",
            summary="The rep is waiting.",
            recommended_option_id="stop",
            options=[
                DecisionOption(
                    id="stop",
                    label="Stop here",
                    consequence="No account change is made.",
                    message_to_send="Thanks, I will decide later.",
                ),
            ],
            holding_message="Please give me a moment.",
        )


@pytest.mark.asyncio
async def test_click_visible_control_tool_clicks_first_matching_frame():
    calls = []

    class FakeFrame:
        def __init__(self, result):
            self.result = result

        async def evaluate(self, script, label):
            calls.append(label)
            return self.result

    class FakePage:
        frames = [
            FakeFrame({"clicked": False, "reason": "missing"}),
            FakeFrame({"clicked": True, "label": "open chat agent", "tag": "BUTTON"}),
        ]

    class FakeSession:
        def __init__(self):
            self.page = FakePage()

        async def get_current_page(self):
            return self.page

    result = await click_visible_control_tool(FakeSession(), "Open Chat Agent")

    assert "Clicked visible control" in result
    assert calls == ["Open Chat Agent", "Open Chat Agent"]


@pytest.mark.asyncio
async def test_click_visible_control_tool_reports_missing_browser():
    result = await click_visible_control_tool(None, "Chat")

    assert result == "No browser session is attached."


def test_outcome_guard_helpers_detect_pending_missing_reference_state():
    details = {
        "outcome": "Membership months will be applied.",
        "confirmation_number": "No separate reference or confirmation number was provided.",
        "amount_saved": "3 months",
        "next_steps": "Follow up later.",
    }
    transcript = "Levi: allow me one moment please:)"

    assert outcome_claims_missing_documentation(details)
    assert text_has_pending_human_work(transcript)


def test_outcome_guard_helpers_detect_pending_support_handoff():
    details = {
        "outcome": "No verified final confirmation was provided.",
        "confirmation_number": None,
        "amount_saved": None,
        "next_steps": "The last verified state was still pending transfer.",
    }
    transcript = "Finn: I'll connect you with our Member Care Team now."

    assert outcome_claims_pending_handoff(details)
    assert text_has_pending_support_handoff(transcript)


def test_find_reference_numbers_prefers_customer_service_reference_context():
    transcript = (
        "Case/code #6721213 was reviewed. "
        "The reference number for your records is #6847916."
    )

    assert find_reference_numbers(transcript) == ["#6721213", "#6847916"]


@pytest.mark.asyncio
async def test_report_outcome_guard_blocks_stale_missing_reference(monkeypatch):
    monkeypatch.setattr(
        user_input_module.settings,
        "agent_pending_outcome_grace_seconds",
        0,
    )

    class FakePage:
        calls = 0

        async def evaluate(self, script):
            self.calls += 1
            if self.calls == 1:
                return "Levi: allow me one moment please:)"
            return "Levi: The reference number for your records is #6847916."

    class FakeSession:
        def __init__(self):
            self.page = FakePage()

        async def get_current_page(self):
            return self.page

    details = {
        "outcome": "The promotion will be applied.",
        "confirmation_number": "No separate reference number was provided.",
        "amount_saved": "3 months",
        "next_steps": "Monitor the account.",
    }

    guard_message = await user_input_module._guard_report_outcome(
        FakeSession(),
        details,
    )

    assert guard_message is not None
    assert "#6847916" in guard_message


@pytest.mark.asyncio
async def test_report_outcome_guard_blocks_unresolved_pending_handoff(monkeypatch):
    monkeypatch.setattr(
        user_input_module.settings,
        "agent_pending_outcome_grace_seconds",
        0,
    )

    class FakePage:
        async def evaluate(self, script):
            return "Finn: I'll connect you with our Member Care Team now."

    class FakeSession:
        async def get_current_page(self):
            return FakePage()

    details = {
        "outcome": "No verified final confirmation was provided.",
        "confirmation_number": None,
        "amount_saved": None,
        "next_steps": "The last verified state was still pending transfer.",
    }

    guard_message = await user_input_module._guard_report_outcome(
        FakeSession(),
        details,
    )

    assert guard_message is not None
    assert "unresolved handoff" in guard_message
