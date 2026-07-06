from src.agent.run_orchestration import build_agent_run_plan, huca_recovery_task


def test_agent_run_plan_normalizes_daemon_payload():
    plan = build_agent_run_plan(
        {
            "task": "Lower my bill.",
            "template": "negotiate_fee",
            "cdp_url": "http://127.0.0.1:9222",
            "target_url": "https://example.com/chat",
            "model": "test-model",
            "max_steps": 12,
        },
        site="generic",
        task_brief="Lower my bill.",
    )

    assert plan.agent_kwargs()["site"] == "generic"
    assert plan.agent_kwargs()["target_url"] == "https://example.com/chat"
    assert plan.execute_kwargs() == {
        "task": "Lower my bill.",
        "template_id": "negotiate_fee",
        "max_steps": 12,
    }


def test_agent_run_plan_carries_mcp_backend():
    plan = build_agent_run_plan(
        {
            "task": "Continue this chat.",
            "target_url": "https://example.com/support",
            "browser_backend": "mcp",
            "mcp_page": {"index": 4, "url": "https://example.com/support"},
        },
        site="generic",
        task_brief="Continue this chat.",
    )

    assert plan.cdp_url is None
    assert plan.browser_backend == "mcp"
    assert plan.agent_kwargs()["browser_backend"] == "mcp"
    assert plan.agent_kwargs()["mcp_page"] == {
        "index": 4,
        "url": "https://example.com/support",
    }


def test_huca_recovery_task_uses_prompt_template():
    task = huca_recovery_task("Ask for a refund.")

    assert "HUCA recovery was explicitly requested" in task
    assert "Original task:\nAsk for a refund." in task
