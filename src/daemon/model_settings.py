"""Local model credential settings for the helper dashboard."""

from __future__ import annotations

import stat
from dataclasses import dataclass
from pathlib import Path

from src.config import USER_ENV_FILE, _read_cliproxyapi_api_key, settings


@dataclass(frozen=True)
class ModelProvider:
    """A dashboard-selectable model provider and its credential field."""

    id: str
    label: str
    key_field: str
    help_text: str


PROVIDERS: tuple[ModelProvider, ...] = (
    ModelProvider(
        id="cliproxyapi",
        label="CLIProxyAPI",
        key_field="cliproxyapi_api_key",
        help_text=(
            "Uses your local CLIProxyAPI server. Leave blank to use the local config fallback."
        ),
    ),
    ModelProvider(
        id="claude",
        label="Claude",
        key_field="anthropic_api_key",
        help_text="Used for Claude Sonnet and Claude Opus runs.",
    ),
    ModelProvider(
        id="openai",
        label="OpenAI",
        key_field="openai_api_key",
        help_text="Used for OpenAI-compatible direct provider runs.",
    ),
    ModelProvider(
        id="gemini-flash",
        label="Gemini",
        key_field="google_api_key",
        help_text="Used for Gemini Flash and Gemini Pro runs.",
    ),
)
PROVIDER_BY_ID = {provider.id: provider for provider in PROVIDERS}
MANAGED_ENV_BY_FIELD = {
    "anthropic_api_key": "ANTHROPIC_API_KEY",
    "openai_api_key": "OPENAI_API_KEY",
    "google_api_key": "GOOGLE_API_KEY",
    "cliproxyapi_api_key": "CLIPROXYAPI_API_KEY",
    "default_llm": "DEFAULT_LLM",
}


def model_settings_payload() -> dict:
    """Return credential presence without exposing secret values."""
    return {
        "ok": True,
        "default_model": settings.default_llm,
        "providers": [
            {
                "id": provider.id,
                "label": provider.label,
                "configured": bool(getattr(settings, provider.key_field, "")),
                "help": provider.help_text,
            }
            for provider in PROVIDERS
        ],
    }


def save_model_settings(
    *,
    default_model: str | None = None,
    provider: str | None = None,
    api_key: str | None = None,
    clear_key: bool = False,
) -> dict:
    """Persist dashboard model settings to the user-local env file."""
    updates: dict[str, str] = {}
    if default_model:
        if default_model not in PROVIDER_BY_ID:
            raise ValueError(f"Unsupported model provider: {default_model}")
        updates["DEFAULT_LLM"] = default_model
        settings.default_llm = default_model

    if provider:
        provider_config = PROVIDER_BY_ID.get(provider)
        if not provider_config:
            raise ValueError(f"Unsupported model provider: {provider}")
        env_name = MANAGED_ENV_BY_FIELD[provider_config.key_field]
        next_key = "" if clear_key else (api_key or "").strip()
        if next_key or clear_key:
            updates[env_name] = next_key
            if clear_key and provider_config.key_field == "cliproxyapi_api_key":
                next_key = _read_cliproxyapi_api_key(settings.cliproxyapi_config)
            setattr(settings, provider_config.key_field, next_key)

    if updates:
        _write_user_env(updates)
    return model_settings_payload()


def _write_user_env(updates: dict[str, str]) -> None:
    """Write managed settings while preserving unrelated lines."""
    USER_ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing_lines = _read_existing_lines(USER_ENV_FILE)
    seen: set[str] = set()
    next_lines: list[str] = []

    for line in existing_lines:
        key = _env_key(line)
        if key in updates:
            seen.add(key)
            value = updates[key]
            if value:
                next_lines.append(f"{key}={_quote_env_value(value)}")
            continue
        next_lines.append(line)

    for key, value in updates.items():
        if key in seen or not value:
            continue
        next_lines.append(f"{key}={_quote_env_value(value)}")

    USER_ENV_FILE.write_text("\n".join(next_lines).rstrip() + "\n", encoding="utf-8")
    try:
        USER_ENV_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def _read_existing_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return [
            "# Flying Pig local model settings",
            "# Managed by the desktop dashboard.",
        ]


def _env_key(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key = stripped.split("=", 1)[0].strip()
    return key if key in set(MANAGED_ENV_BY_FIELD.values()) else None


def _quote_env_value(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
