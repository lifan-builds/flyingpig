"""Decision Checkpoint schema and answer semantics."""

from __future__ import annotations

import json
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class DecisionOption(BaseModel):
    id: str
    label: str
    consequence: str
    message_to_send: str | None = None

    @field_validator("id", "label", "consequence")
    @classmethod
    def require_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("message_to_send")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class DecisionCheckpointParams(BaseModel):
    checkpoint_id: str = Field(default_factory=lambda: f"cp_{uuid4().hex[:12]}")
    type: Literal[
        "strategy_pivot",
        "offer_choice",
        "irreversible_action",
        "verification",
        "timeout_risk",
    ]
    summary: str
    recommended_option_id: str
    options: list[DecisionOption]
    holding_message: str | None = None
    holding_message_after_seconds: int | None = None

    @field_validator("summary", "recommended_option_id")
    @classmethod
    def require_checkpoint_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("holding_message")
    @classmethod
    def normalize_holding_message(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def validate_checkpoint(self):
        if not self.options:
            raise ValueError("decision checkpoint must include at least one option")

        option_ids = [option.id for option in self.options]
        if len(option_ids) != len(set(option_ids)):
            raise ValueError("decision checkpoint option ids must be unique")

        if self.recommended_option_id not in option_ids:
            raise ValueError("recommended_option_id must match one option id")

        if self.type == "irreversible_action":
            missing_message = [option.id for option in self.options if not option.message_to_send]
            if missing_message:
                raise ValueError(
                    "irreversible_action options must include exact message_to_send: "
                    + ", ".join(missing_message)
                )

        if self.holding_message and not self.holding_message_after_seconds:
            raise ValueError("holding_message requires holding_message_after_seconds")
        if self.holding_message_after_seconds and not self.holding_message:
            raise ValueError("holding_message_after_seconds requires holding_message")
        if (
            self.holding_message_after_seconds is not None
            and self.holding_message_after_seconds < 1
        ):
            raise ValueError("holding_message_after_seconds must be positive")

        return self


def build_pending_request(params: DecisionCheckpointParams) -> dict:
    """Return the reconnect-safe request envelope used by helper clients."""
    return {
        "type": "decision_checkpoint",
        "checkpoint": params.model_dump(),
    }


def parse_answer(params: DecisionCheckpointParams, raw: str) -> dict:
    """Parse a dashboard or CLI answer into the canonical answer envelope."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return coerce_answer(params, raw)

    if not isinstance(data, dict):
        return coerce_answer(params, raw)
    selected_option_id = str(data.get("selected_option_id") or data.get("option_id") or "")
    checkpoint_id = str(data.get("checkpoint_id") or params.checkpoint_id)
    option = find_option(params, selected_option_id)
    selected_message = data.get("selected_message")
    if option and not selected_message:
        selected_message = option.message_to_send
    return {
        "checkpoint_id": checkpoint_id,
        "expected_checkpoint_id": params.checkpoint_id,
        "checkpoint_id_matches": checkpoint_id == params.checkpoint_id,
        "selected_option_id": selected_option_id if option else "custom",
        "selected_message": selected_message,
        "free_text": None if option else data.get("free_text") or selected_option_id,
        "is_holding_message": False,
    }


def coerce_answer(params: DecisionCheckpointParams, response: str) -> dict:
    """Turn a plain option id or free-text response into an answer envelope."""
    option = find_option(params, response)
    if option:
        return {
            "checkpoint_id": params.checkpoint_id,
            "expected_checkpoint_id": params.checkpoint_id,
            "checkpoint_id_matches": True,
            "selected_option_id": option.id,
            "selected_message": option.message_to_send,
            "free_text": None,
            "is_holding_message": False,
        }
    return {
        "checkpoint_id": params.checkpoint_id,
        "expected_checkpoint_id": params.checkpoint_id,
        "checkpoint_id_matches": True,
        "selected_option_id": "custom",
        "selected_message": None,
        "free_text": response,
        "is_holding_message": False,
    }


def holding_message_answer(params: DecisionCheckpointParams) -> dict:
    """Return the canonical answer envelope for a model-authored holding message."""
    return {
        "checkpoint_id": params.checkpoint_id,
        "expected_checkpoint_id": params.checkpoint_id,
        "checkpoint_id_matches": True,
        "selected_option_id": "__holding_message__",
        "selected_message": params.holding_message,
        "is_holding_message": True,
        "instruction": (
            "Send selected_message exactly as a neutral holding message, "
            "then raise the same decision checkpoint again."
        ),
    }


def find_option(
    params: DecisionCheckpointParams,
    option_id: str,
) -> DecisionOption | None:
    normalized = option_id.strip().lower()
    return next((option for option in params.options if option.id.lower() == normalized), None)
