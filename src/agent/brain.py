"""Core agent brain: coordinates a customer-service run."""

import logging
from datetime import UTC, datetime
from pathlib import Path

from browser_use import Agent
from browser_use.agent.views import AgentHistoryList

from src.agent.detector import ChatbotDetector
from src.agent.escalator import EscalationManager
from src.agent.evidence import EvidenceRecorder
from src.agent.llm_runtime import create_llm
from src.agent.navigator import ChatNavigator
from src.agent.result import TaskResult, TaskStatus
from src.agent.user_input import UserInputHandler, build_tools
from src.config import settings
from src.sites.registry import get_site_adapter

logger = logging.getLogger(__name__)

# Backwards-compatible import surface for tests and scripts.
_build_tools = build_tools


class AgentBrain:
    """Top-level orchestrator that drives the customer service interaction."""

    def __init__(
        self,
        site: str,
        headless: bool = True,
        input_mode: str = "cli",
        model: str | None = None,
        cdp_url: str | None = None,
        target_url: str | None = None,
        browser_mode: str = "controlled",
        navigate_on_attach: bool = False,
        use_vision: bool = True,
        llm_timeout: int = 180,
        fallback_model: str | None = None,
    ):
        self.site_adapter = get_site_adapter(site)
        self.headless = headless
        self.cdp_url = cdp_url
        self.target_url = target_url
        self.browser_mode = browser_mode
        self.navigate_on_attach = navigate_on_attach
        self.use_vision = use_vision
        self.llm_timeout = llm_timeout
        self.fallback_model = fallback_model or settings.default_fallback_llm or None
        self.detector = ChatbotDetector()
        self.escalation = EscalationManager()
        self.input_handler = UserInputHandler(mode=input_mode)
        self.evidence = EvidenceRecorder(self.site_adapter)
        self._model_name = model
        self.llm = self._create_llm()
        self.fallback_llm = create_llm(self.fallback_model) if self.fallback_model else None
        self._step_log: list[dict] = []

    @property
    def step_log(self) -> list[dict]:
        """Return a copy of user-facing progress events for active runs."""
        return list(self._step_log)

    def _create_llm(self):
        return create_llm(self._model_name)

    async def _on_step_start(self, agent: Agent):
        """Called at the start of each agent step."""
        step_num = agent.state.n_steps
        self._step_log.append({
            "step": step_num,
            "phase": "starting",
            "message": f"Step {step_num} started",
            "timestamp": datetime.now(UTC).isoformat(),
        })
        logger.info("Step %s starting...", step_num)

    async def _on_step_end(self, agent: Agent):
        """Called at the end of each agent step. Logs step details."""
        step_num = agent.state.n_steps
        history = agent.history
        if history.history:
            last = history.history[-1]
            thought = ""
            goal = ""
            if last.model_output:
                thought = last.model_output.thinking or ""
                goal = last.model_output.next_goal or ""
            self._step_log.append({
                "step": step_num,
                "phase": "complete",
                "thought": thought[:200],
                "goal": goal[:200],
                "message": goal[:200] or thought[:200] or f"Step {step_num} complete",
                "timestamp": datetime.now(UTC).isoformat(),
            })
        logger.info("Step %s complete.", step_num)

    def _save_session(self, history: AgentHistoryList, save_dir: Path) -> str:
        """Compatibility wrapper around the evidence Module."""
        return self.evidence.save_session(history, save_dir)

    async def _capture_chat_transcript(self, browser_session) -> list[str]:
        """Compatibility wrapper around the evidence Module."""
        return await self.evidence.capture_chat_transcript(browser_session)

    def _extract_chat_transcript_from_history(
        self,
        history: AgentHistoryList,
    ) -> list[str]:
        """Compatibility wrapper around the evidence Module."""
        return self.evidence.extract_chat_transcript_from_history(history)

    def _extract_result(
        self,
        history: AgentHistoryList,
        chat_transcript: list[str] | None = None,
    ) -> TaskResult:
        """Compatibility wrapper around the evidence Module."""
        return self.evidence.extract_result(history, chat_transcript=chat_transcript)

    async def execute(
        self,
        task: str,
        dry_run: bool = False,
        max_steps: int = 100,
        save_dir: str | Path = "recordings",
        template_id: str | None = None,
    ) -> TaskResult:
        """Execute a customer service task end-to-end."""
        navigator = ChatNavigator(
            site_adapter=self.site_adapter,
            headless=self.headless,
            cdp_url=self.cdp_url,
            target_url=self.target_url,
            browser_mode=self.browser_mode,
            navigate_on_attach=self.navigate_on_attach,
        )
        self._step_log = []

        try:
            agent_task = self._build_agent_task(task=task, template_id=template_id)
            if dry_run:
                return TaskResult(
                    status=TaskStatus.SUCCESS,
                    summary=f"[DRY RUN] Would execute on {self.site_adapter.name}: {task}",
                    outcome_details={
                        "prompt_length": len(agent_task),
                        "prompt_preview": agent_task[:500],
                        "template": template_id or "none",
                    },
                )

            browser_session = await navigator.open_chat()
            if self.site_adapter.requires_login:
                await navigator.wait_for_login(self.input_handler)

            try:
                history = await self._run_browser_use_agent(
                    agent_task=agent_task,
                    llm=self.llm,
                    browser_session=browser_session,
                    max_steps=max_steps,
                    save_dir=save_dir,
                )
            except Exception as primary_error:
                if self.fallback_llm is None:
                    raise
                logger.exception(
                    "Primary LLM failed; retrying current browser state with fallback %s",
                    self.fallback_model,
                )
                history = await self._run_browser_use_agent(
                    agent_task=self._fallback_agent_task(agent_task, primary_error),
                    llm=self.fallback_llm,
                    browser_session=browser_session,
                    max_steps=max_steps,
                    save_dir=save_dir,
                )
            chat_transcript = await self.evidence.capture_chat_transcript(browser_session)
            if not chat_transcript:
                chat_transcript = self.evidence.extract_chat_transcript_from_history(history)

            save_path = self.evidence.save_session(history, Path(save_dir))
            result = self.evidence.extract_result(history, chat_transcript=chat_transcript)
            result.transcript_path = save_path
            return result

        except Exception as e:
            logger.exception("Task failed: %s", e)
            return TaskResult(
                status=TaskStatus.FAILED,
                summary=f"Task failed: {e}",
                transcript=[f"Error: {e}"],
            )
        finally:
            await navigator.close()

    async def _run_browser_use_agent(
        self,
        *,
        agent_task: str,
        llm,
        browser_session,
        max_steps: int,
        save_dir: str | Path,
    ):
        agent = Agent(
            task=agent_task,
            llm=llm,
            browser_session=browser_session,
            tools=build_tools(self.input_handler),
            use_vision=self.use_vision,
            max_actions_per_step=2,
            max_failures=5,
            llm_timeout=self.llm_timeout,
            generate_gif=True,
            save_conversation_path=str(Path(save_dir) / "conversation.json"),
        )
        return await agent.run(
            max_steps=max_steps,
            on_step_start=self._on_step_start,
            on_step_end=self._on_step_end,
        )

    def _build_agent_task(self, *, task: str, template_id: str | None) -> str:
        agent_task = self.site_adapter.build_task_prompt(
            user_task=task,
            escalation_instructions=self.escalation.get_instructions(),
            detection_instructions=self.detector.get_instructions(),
            template_id=template_id,
        )
        if not self.cdp_url:
            return agent_task
        return (
            "## Attached-Browser Mode\n"
            "You are operating inside a Chrome tab that was attached "
            "over CDP. Do NOT open new tabs. If you need to reach the "
            "site's chat page, reuse the current tab only.\n\n"
            "**First-step rule:** If the page appears empty or "
            "partially loaded (low element count, SPA skeleton, "
            "loading spinners), use the `wait` action — do NOT "
            "conclude the user is on the wrong page and do NOT call "
            "ask_user yet. Many target sites are SPAs that take 3-10 "
            "seconds to render after attach. Only if the URL itself "
            "is clearly unrelated to the task should you ask_user to "
            "navigate.\n\n"
        ) + agent_task

    def _fallback_agent_task(self, agent_task: str, primary_error: Exception) -> str:
        return (
            "## Fallback-LLM Continuation\n"
            "The previous model failed while this browser session was active. "
            "Continue from the current visible page and chat state. Do not restart "
            "the task or open a new tab unless the current page is unusable. "
            f"Previous failure: {type(primary_error).__name__}: {primary_error}\n\n"
        ) + agent_task
