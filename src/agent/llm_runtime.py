"""LLM adapter selection for customer-service runs."""

from browser_use.llm import ChatAnthropic, ChatGoogle, ChatOpenAI

from src.config import settings


def create_llm(model_name: str | None = None):
    """Create the configured browser-use LLM adapter."""
    model_name = model_name or settings.default_llm

    if model_name in ("claude", "claude-sonnet"):
        return ChatAnthropic(
            model="claude-sonnet-4-5",
            api_key=settings.anthropic_api_key,
        )
    if model_name == "claude-opus":
        return ChatAnthropic(
            model="claude-opus-4-5",
            api_key=settings.anthropic_api_key,
        )
    if model_name in ("openai", "gpt-4o"):
        return ChatOpenAI(
            model="gpt-4o",
            api_key=settings.openai_api_key,
        )
    if model_name in ("cliproxyapi", "cliproxy", "gpt-5.5"):
        return ChatOpenAI(
            model=settings.cliproxyapi_model,
            api_key=settings.cliproxyapi_api_key,
            base_url=settings.cliproxyapi_base_url,
        )
    if model_name in ("gemini", "gemini-flash"):
        return ChatGoogle(
            model="gemini-2.5-flash",
            api_key=settings.google_api_key,
        )
    if model_name == "gemini-pro":
        return ChatGoogle(
            model="gemini-2.5-pro",
            api_key=settings.google_api_key,
        )
    return ChatAnthropic(
        model="claude-sonnet-4-5",
        api_key=settings.anthropic_api_key,
    )
