import json

from src.agent.decision_checkpoint import (
    DecisionCheckpointParams,
    DecisionOption,
    build_pending_request,
    holding_message_answer,
    parse_answer,
)


def test_build_pending_request_uses_canonical_checkpoint_envelope():
    params = DecisionCheckpointParams(
        checkpoint_id="cp_contract",
        type="offer_choice",
        summary="Amex offered 10,000 points.",
        recommended_option_id="accept",
        options=[
            DecisionOption(
                id="accept",
                label="Accept offer",
                consequence="The user keeps the card with the offered bonus.",
                message_to_send="I would like to accept the offer.",
            ),
        ],
    )

    request = build_pending_request(params)

    assert request["type"] == "decision_checkpoint"
    assert request["checkpoint"]["checkpoint_id"] == "cp_contract"
    assert request["checkpoint"]["options"][0]["message_to_send"]


def test_parse_answer_fills_selected_message_from_option():
    params = DecisionCheckpointParams(
        checkpoint_id="cp_answer",
        type="strategy_pivot",
        summary="No retention offer is available.",
        recommended_option_id="close",
        options=[
            DecisionOption(
                id="close",
                label="Close card",
                consequence="Proceed toward cancellation.",
                message_to_send="I would like to proceed toward closing the card.",
            ),
        ],
    )

    answer = parse_answer(
        params,
        json.dumps(
            {
                "checkpoint_id": "cp_answer",
                "selected_option_id": "close",
            }
        ),
    )

    assert answer["selected_option_id"] == "close"
    assert answer["selected_message"] == "I would like to proceed toward closing the card."
    assert answer["checkpoint_id_matches"] is True


def test_holding_message_answer_carries_no_improvised_action():
    params = DecisionCheckpointParams(
        checkpoint_id="cp_hold",
        type="timeout_risk",
        summary="The rep is waiting.",
        recommended_option_id="wait",
        options=[
            DecisionOption(
                id="wait",
                label="Wait for user",
                consequence="No account change is made.",
                message_to_send="Please give me a moment to review this.",
            ),
        ],
        holding_message="Please give me a moment to review this.",
        holding_message_after_seconds=1,
    )

    answer = holding_message_answer(params)

    assert answer["selected_option_id"] == "__holding_message__"
    assert answer["selected_message"] == "Please give me a moment to review this."
    assert answer["is_holding_message"] is True
