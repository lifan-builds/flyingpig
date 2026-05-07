"""User interaction tools for agent runs."""

import asyncio
import json
import logging

from browser_use.agent.views import ActionResult
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AskUserParams(BaseModel):
    question: str
    reason: str


class ReportOutcomeParams(BaseModel):
    outcome: str
    confirmation_number: str | None = None
    amount_saved: str | None = None
    next_steps: str | None = None


class ReportDetectionParams(BaseModel):
    responder_type: str
    confidence: str
    evidence: str


class UserInputHandler:
    """Handles user input requests from the agent."""

    def __init__(self, mode: str = "cli"):
        self.mode = mode
        self._pending_question: str | None = None
        self._response_queue: asyncio.Queue[str] = asyncio.Queue()

    async def ask(self, question: str, reason: str) -> str:
        """Ask the user for input and wait for response."""
        if self.mode == "cli":
            return await self._ask_cli(question, reason)
        return await self._ask_api(question, reason)

    async def _ask_cli(self, question: str, reason: str) -> str:
        """Interactive CLI prompt; runs input() in a thread to avoid blocking."""
        print(f"\n{'=' * 60}")
        print("🐷 AGENT NEEDS YOUR INPUT")
        print(f"{'=' * 60}")
        print(f"Question: {question}")
        print(f"Reason: {reason}")
        print(f"{'=' * 60}")

        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: input("Your answer: ").strip(),
            )
        except EOFError as e:
            raise RuntimeError(
                "Interactive input is not available. Run this command in the foreground "
                "so you can answer login and confirmation prompts."
            ) from e
        return response

    async def _ask_api(self, question: str, reason: str) -> str:
        """API mode: store the question and wait for response via queue."""
        self._pending_question = question
        logger.info("Waiting for user input: %s (reason: %s)", question, reason)
        response = await self._response_queue.get()
        self._pending_question = None
        return response

    def provide_input(self, response: str) -> None:
        """Provide a response to a pending question."""
        self._response_queue.put_nowait(response)

    @property
    def pending_question(self) -> str | None:
        return self._pending_question


def build_tools(input_handler: UserInputHandler | None = None):
    """Create custom tools the agent can use during chat interactions."""
    from browser_use.tools.service import Tools

    tools = Tools()

    @tools.registry.action(
        "Ask the user for information you need but don't have. "
        "Use this when the site asks for login credentials, verification codes, "
        "last 4 digits of a card, zip code, or any personal information. "
        "NEVER guess or fabricate this information.",
        param_model=AskUserParams,
    )
    async def ask_user(params: AskUserParams):
        if input_handler:
            response = await input_handler.ask(params.question, params.reason)
            logger.info("User responded to: %s", params.question)
            return ActionResult(
                extracted_content=f"User responded: {response}",
                long_term_memory=f"User provided: {response}",
            )

        logger.info("Agent needs input: %s (reason: %s)", params.question, params.reason)
        return ActionResult(
            extracted_content=f"[NEEDS_INPUT] {params.question}",
            is_done=True,
        )

    @tools.registry.action(
        "Report the final outcome of the customer service interaction. "
        "Call this when the conversation is complete and you have a result.",
        param_model=ReportOutcomeParams,
    )
    async def report_outcome(params: ReportOutcomeParams):
        details = {
            "outcome": params.outcome,
            "confirmation_number": params.confirmation_number,
            "amount_saved": params.amount_saved,
            "next_steps": params.next_steps,
        }
        logger.info("Task outcome: %s", json.dumps(details))
        return ActionResult(
            extracted_content=json.dumps(details),
            is_done=True,
        )

    @tools.registry.action(
        "Report your assessment of whether the chat responder is an AI chatbot "
        "or a human representative. Call this after your third exchange.",
        param_model=ReportDetectionParams,
    )
    async def report_detection(params: ReportDetectionParams):
        next_step = (
            "Proceeding with escalation."
            if params.responder_type == "ai_chatbot"
            else "Proceeding with negotiation."
        )
        logger.info(
            "Detection: %s (confidence: %s, evidence: %s)",
            params.responder_type,
            params.confidence,
            params.evidence,
        )
        return ActionResult(
            extracted_content=(
                f"Detected: {params.responder_type} ({params.confidence} confidence). "
                f"Evidence: {params.evidence}"
            ),
            long_term_memory=(
                f"Responder is {params.responder_type}. "
                f"{next_step}"
            ),
        )

    return tools
