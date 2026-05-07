"""Tests for application settings."""

from src.config import Settings


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
