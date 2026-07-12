"""Structured user authorization for supervised customer-service runs."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class RunAuthorization(BaseModel):
    """Consequential actions and boundaries explicitly authorized by the user."""

    target_account: str | None = None
    authorized_actions: list[str] = Field(default_factory=list)
    refund_methods: list[str] = Field(default_factory=list)
    declined_alternatives: list[str] = Field(default_factory=list)
    huca_authorized: bool = False
    user_authorized: bool = False

    @field_validator(
        "authorized_actions",
        "refund_methods",
        "declined_alternatives",
        mode="before",
    )
    @classmethod
    def normalize_lists(cls, value):
        if value is None:
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def permits(self, action: str) -> bool:
        """Return whether an action is explicitly authorized."""
        return self.user_authorized and action in self.authorized_actions


def authorization_from_payload(payload: dict | None) -> RunAuthorization:
    """Build authorization from a run payload without inferring sensitive scope."""
    payload = payload or {}
    raw = payload.get("authorization")
    if isinstance(raw, dict):
        data = dict(raw)
        data.setdefault("user_authorized", bool(payload.get("user_authorized")))
        return RunAuthorization(**data)
    return RunAuthorization(user_authorized=bool(payload.get("user_authorized")))
