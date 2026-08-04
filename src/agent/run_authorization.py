"""Structured user authorization for supervised customer-service runs."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AuthorizationTarget(BaseModel):
    """One concrete target and the consequential actions permitted for it."""

    model_config = ConfigDict(extra="forbid")

    key: str
    display: str
    authorized_actions: list[str] = Field(default_factory=list)

    @field_validator("key", "display", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> str:
        return str(value or "").strip()

    @field_validator("authorized_actions", mode="before")
    @classmethod
    def normalize_actions(cls, value: object) -> list[str]:
        if value is None:
            return []
        return list(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))

    @model_validator(mode="after")
    def require_identity(self) -> AuthorizationTarget:
        if not self.key or not self.display:
            raise ValueError("authorization targets require non-empty key and display values")
        return self


class RunAuthorization(BaseModel):
    """Consequential actions and boundaries explicitly authorized by the user.

    ``target_account`` and global ``authorized_actions`` are retained only as a
    narrow single-target migration input. New callers should send ``targets``.
    """

    model_config = ConfigDict(extra="forbid")

    targets: list[AuthorizationTarget] = Field(default_factory=list)
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
    def normalize_lists(cls, value: object) -> list[str]:
        if value is None:
            return []
        return list(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))

    @field_validator("target_account", mode="before")
    @classmethod
    def normalize_legacy_target(cls, value: object) -> str | None:
        normalized = str(value or "").strip()
        return normalized or None

    @model_validator(mode="after")
    def normalize_legacy_single_target(self) -> RunAuthorization:
        if self.targets:
            # Global legacy permissions must never broaden structured targets.
            self.target_account = None
            self.authorized_actions = []
            self._validate_unique_target_keys()
            return self
        if self.target_account:
            self.targets = [
                AuthorizationTarget(
                    key="legacy-target",
                    display=self.target_account,
                    authorized_actions=self.authorized_actions,
                )
            ]
        return self

    def _validate_unique_target_keys(self) -> None:
        keys = [target.key for target in self.targets]
        if len(keys) != len(set(keys)):
            raise ValueError("authorization target keys must be unique")

    def permits(self, action: str, target_key: str | None = None) -> bool:
        """Return whether an action is explicitly authorized for a concrete target."""
        if not self.user_authorized:
            return False
        matches = self.targets_for_action(action)
        if target_key is None:
            return len(matches) == 1
        return any(target.key == target_key for target in matches)

    def targets_for_action(self, action: str) -> list[AuthorizationTarget]:
        """Return ordered targets that explicitly permit ``action``."""
        if not self.user_authorized:
            return []
        return [target for target in self.targets if action in target.authorized_actions]

    def target(self, target_key: str | None) -> AuthorizationTarget | None:
        """Resolve an exact target key, or the sole target when unambiguous."""
        if target_key:
            return next((target for target in self.targets if target.key == target_key), None)
        return self.targets[0] if len(self.targets) == 1 else None

    def target_for_visible_text(
        self,
        action: str,
        visible_text: str,
    ) -> AuthorizationTarget | None:
        """Resolve a permitted target only when visible text makes it unambiguous."""
        candidates = self.targets_for_action(action)
        if len(candidates) == 1:
            return candidates[0]
        lowered = visible_text.casefold()
        matches = [target for target in candidates if target.display.casefold() in lowered]
        return matches[0] if len(matches) == 1 else None


def authorization_from_payload(payload: dict | None) -> RunAuthorization:
    """Build authorization from a run payload without inferring sensitive scope."""
    payload = payload or {}
    raw = payload.get("authorization")
    if isinstance(raw, dict):
        data = dict(raw)
        data.setdefault("user_authorized", bool(payload.get("user_authorized")))
        return RunAuthorization(**data)
    return RunAuthorization(user_authorized=bool(payload.get("user_authorized")))
