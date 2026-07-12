"""LLM adapter selection and health checks for customer-service runs."""

from __future__ import annotations

import asyncio

from browser_use.llm import ChatAnthropic, ChatGoogle, ChatOpenAI
from openai import AsyncOpenAI

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
    if model_name in (
        "cliproxyapi",
        "cliproxy",
        "gpt-5.5",
        "gpt-5.4-mini",
        "gpt-5.4",
        "gpt-5.6-luna",
        "gpt-5.6-sol",
        "gpt-5.6-terra",
    ):
        local_model = (
            settings.cliproxyapi_model if model_name in ("cliproxyapi", "cliproxy") else model_name
        )
        return ChatOpenAI(
            model=local_model,
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


async def select_healthy_cliproxy_llm(
    *,
    preferred_model: str | None = None,
    timeout_seconds: int | None = None,
) -> tuple[object, str, list[dict]]:
    """Select the first responsive local CLIProxy model using a harmless probe."""
    timeout = timeout_seconds or settings.model_probe_timeout_seconds
    client = AsyncOpenAI(
        api_key=settings.cliproxyapi_api_key,
        base_url=settings.cliproxyapi_base_url,
        timeout=float(timeout),
        max_retries=0,
    )
    available = await _cliproxy_model_ids(client, timeout)
    candidates = _ordered_cliproxy_candidates(available, preferred_model)
    probes: list[dict] = []
    for model in candidates:
        try:
            await asyncio.wait_for(
                client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "Reply with exactly: pong"}],
                    max_tokens=16,
                ),
                timeout=max(timeout, 1),
            )
        except Exception as exc:
            probes.append({"model": model, "ok": False, "error": type(exc).__name__})
            continue
        probes.append({"model": model, "ok": True})
        return create_llm(model), model, probes
    raise RuntimeError(f"No healthy CLIProxy model found: {probes}")


async def _cliproxy_model_ids(client: AsyncOpenAI, timeout: int) -> list[str]:
    response = await asyncio.wait_for(client.models.list(), timeout=max(timeout, 1))
    return [item.id for item in response.data]


def _ordered_cliproxy_candidates(available: list[str], preferred_model: str | None) -> list[str]:
    order = ["gpt-5.6-luna", "gpt-5.4-mini", preferred_model, "gpt-5.5", "gpt-5.4"]
    result: list[str] = []
    for model in order:
        if model and model in available and model not in result:
            result.append(model)
    return result
