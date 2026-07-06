"""Prepared customer-service run plans for AgentBrain callers."""

from __future__ import annotations

from dataclasses import dataclass

from src.sites.task_templates import load_prompt_template


@dataclass(frozen=True)
class AgentRunPlan:
    """Normalized plan for one supervised browser-use run."""

    site: str
    task: str
    user_task: str
    template_id: str | None
    cdp_url: str | None
    target_url: str | None
    max_steps: int
    navigate_on_attach: bool
    model: str | None
    fallback_model: str | None
    permission_mode: str
    browser_backend: str = "browser_use"
    mcp_page: dict | None = None

    def agent_kwargs(self) -> dict:
        """Return the AgentBrain construction kwargs for this run."""
        return {
            "site": self.site,
            "headless": False,
            "input_mode": "api",
            "model": self.model,
            "fallback_model": self.fallback_model,
            "cdp_url": self.cdp_url,
            "target_url": self.target_url,
            "navigate_on_attach": self.navigate_on_attach,
            "browser_backend": self.browser_backend,
            "mcp_page": self.mcp_page,
        }

    def execute_kwargs(self) -> dict:
        """Return the AgentBrain.execute kwargs for this run."""
        return {
            "task": self.task,
            "template_id": self.template_id,
            "max_steps": self.max_steps,
        }


def build_agent_run_plan(
    msg: dict,
    *,
    site: str,
    task_brief: str,
    huca: bool = False,
) -> AgentRunPlan:
    """Normalize daemon start payloads into a prepared AgentBrain run plan."""
    target_url = msg.get("target_url") or msg.get("url") or None
    task = huca_recovery_task(task_brief) if huca else task_brief
    return AgentRunPlan(
        site=site,
        task=task,
        user_task=msg.get("task") or "",
        template_id=msg.get("template") or None,
        cdp_url=msg.get("cdp_url") or None,
        target_url=target_url,
        max_steps=msg.get("max_steps", 30),
        navigate_on_attach=bool(msg.get("navigate_on_attach")),
        model=msg.get("model"),
        fallback_model=msg.get("fallback_model"),
        permission_mode=msg.get("permission_mode") or "supervised_browser",
        browser_backend=msg.get("browser_backend") or "browser_use",
        mcp_page=msg.get("mcp_page") or None,
    )


def huca_recovery_task(task: str) -> str:
    """Render the HUCA recovery wrapper from the generic prompt template."""
    return load_prompt_template("generic", "huca_recovery.txt").replace("{task}", task)
