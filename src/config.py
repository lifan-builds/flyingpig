import os
import re
from pathlib import Path

from pydantic_settings import BaseSettings

USER_ENV_FILE = Path(os.environ.get("FLYINGPIG_USER_ENV", "~/.flyingpig/.env")).expanduser()


def _read_cliproxyapi_api_key(config_path: str) -> str:
    path = Path(config_path).expanduser()
    try:
        config_text = path.read_text(encoding="utf-8")
    except OSError:
        return ""

    match = re.search(r'["\']?(sk-local-[A-Za-z0-9_-]+)["\']?', config_text)
    return match.group(1) if match else ""


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    cliproxyapi_api_key: str = ""
    api_secret_key: str = ""
    cliproxyapi_base_url: str = "http://127.0.0.1:8317/v1"
    cliproxyapi_model: str = "gpt-5.5"
    cliproxyapi_config: str = "~/.cli-proxy-api/config.yaml"
    database_url: str = "postgresql+asyncpg://flyingpig:flyingpig@localhost:5432/flyingpig"
    redis_url: str = "redis://localhost:6379/0"
    app_env: str = "development"
    log_level: str = "INFO"
    default_llm: str = "claude"
    default_fallback_llm: str = ""
    browser_headless: bool = True
    recordings_dir: str = "recordings"
    max_interaction_minutes: int = 15
    agent_max_actions_per_step: int = 4
    agent_pending_outcome_grace_seconds: int = 75
    browser_viewport_width: int = 1920
    browser_viewport_height: int = 1080

    model_config = {
        "env_file": (".env", str(USER_ENV_FILE)),
        "env_file_encoding": "utf-8",
    }

    def model_post_init(self, __context: object) -> None:
        if not self.cliproxyapi_api_key:
            self.cliproxyapi_api_key = _read_cliproxyapi_api_key(self.cliproxyapi_config)


settings = Settings()
