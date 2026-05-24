"""Tests for application settings."""

from src.config import Settings
from src.daemon import model_settings


def test_cliproxyapi_key_loads_from_config_file(tmp_path, monkeypatch):
    monkeypatch.delenv("CLIPROXYAPI_API_KEY", raising=False)
    config_path = tmp_path / "cliproxyapi.yaml"
    config_path.write_text(
        """
host: "127.0.0.1"
port: 8317
api-keys:
  - "sk-local-test-key"
""",
        encoding="utf-8",
    )

    settings = Settings(cliproxyapi_config=str(config_path), _env_file=None)

    assert settings.cliproxyapi_api_key == "sk-local-test-key"


def test_dashboard_model_settings_write_user_env(tmp_path, monkeypatch):
    env_path = tmp_path / ".flyingpig.env"
    monkeypatch.setattr(model_settings, "USER_ENV_FILE", env_path)
    monkeypatch.setattr(model_settings.settings, "default_llm", "claude")
    monkeypatch.setattr(model_settings.settings, "anthropic_api_key", "")

    payload = model_settings.save_model_settings(
        default_model="claude",
        provider="claude",
        api_key="sk-ant-test",
    )

    assert payload["default_model"] == "claude"
    assert any(
        provider["id"] == "claude" and provider["configured"]
        for provider in payload["providers"]
    )
    text = env_path.read_text(encoding="utf-8")
    assert 'DEFAULT_LLM="claude"' in text
    assert 'ANTHROPIC_API_KEY="sk-ant-test"' in text

    cleared = model_settings.save_model_settings(provider="claude", clear_key=True)

    assert not any(
        provider["id"] == "claude" and provider["configured"]
        for provider in cleared["providers"]
    )
    assert "ANTHROPIC_API_KEY" not in env_path.read_text(encoding="utf-8")
