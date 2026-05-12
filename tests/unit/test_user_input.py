import asyncio
import json

import pytest
from pydantic import ValidationError
from src.agent.user_input import (
    DecisionCheckpointParams,
    DecisionOption,
    UserInputHandler,
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
