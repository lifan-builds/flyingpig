from types import SimpleNamespace

import pytest
from src.agent import llm_runtime


def test_ordered_cliproxy_candidates_prefers_small_healthy_models():
    candidates = llm_runtime._ordered_cliproxy_candidates(
        ["gpt-5.5", "gpt-5.4-mini", "gpt-5.6-luna"],
        "gpt-5.5",
    )

    assert candidates == ["gpt-5.6-luna", "gpt-5.4-mini", "gpt-5.5"]


@pytest.mark.asyncio
async def test_select_healthy_cliproxy_skips_quota_blocked_model(monkeypatch):
    class FakeModels:
        async def list(self):
            return SimpleNamespace(
                data=[
                    SimpleNamespace(id="gpt-5.6-luna"),
                    SimpleNamespace(id="gpt-5.4-mini"),
                ]
            )

    class FakeCompletions:
        async def create(self, *, model, **kwargs):
            if model == "gpt-5.6-luna":
                raise RuntimeError("usage_limit_reached")
            return SimpleNamespace(choices=[])

    class FakeClient:
        def __init__(self, **kwargs):
            self.models = FakeModels()
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr(llm_runtime, "AsyncOpenAI", FakeClient)
    monkeypatch.setattr(llm_runtime, "create_llm", lambda model: f"llm:{model}")

    llm, selected, probes = await llm_runtime.select_healthy_cliproxy_llm(
        preferred_model="gpt-5.5",
        timeout_seconds=1,
    )

    assert llm == "llm:gpt-5.4-mini"
    assert selected == "gpt-5.4-mini"
    assert probes == [
        {"model": "gpt-5.6-luna", "ok": False, "error": "RuntimeError"},
        {"model": "gpt-5.4-mini", "ok": True},
    ]
