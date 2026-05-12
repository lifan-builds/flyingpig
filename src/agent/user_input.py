"""User interaction tools for agent runs."""

import asyncio
import json
import logging
from datetime import UTC, datetime

from browser_use.agent.views import ActionResult
from pydantic import BaseModel

from src.agent.decision_checkpoint import (
    DecisionCheckpointParams,
    DecisionOption,
    build_pending_request,
    coerce_answer,
    holding_message_answer,
    parse_answer,
)

logger = logging.getLogger(__name__)

__all__ = [
    "AskUserParams",
    "DecisionCheckpointParams",
    "DecisionOption",
    "ReportDetectionParams",
    "ReportOutcomeParams",
    "UserInputHandler",
    "build_tools",
]


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
        self._pending_request: dict | None = None
        self._response_queue: asyncio.Queue[str] = asyncio.Queue()
        self._events: list[dict] = []

    async def ask(self, question: str, reason: str) -> str:
        """Ask the user for input and wait for response."""
        if self.mode == "cli":
            return await self._ask_cli(question, reason)
        return await self._ask_api(question, reason)

    async def decision_checkpoint(self, params: DecisionCheckpointParams) -> str:
        """Ask the user to choose a consequential next step."""
        if self.mode == "cli":
            return await self._decision_checkpoint_cli(params)
        return await self._decision_checkpoint_api(params)

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
        self._pending_request = {
            "type": "question",
            "question": question,
            "reason": reason,
        }
        self._record_event("question_opened", self._pending_request)
        logger.info("Waiting for user input: %s (reason: %s)", question, reason)
        response = await self._response_queue.get()
        self._record_event(
            "question_answered",
            {
                "question": question,
                "response": response,
            },
        )
        self._pending_question = None
        self._pending_request = None
        return response

    async def _decision_checkpoint_cli(self, params: DecisionCheckpointParams) -> str:
        """Interactive CLI checkpoint with explicit choices."""
        print(f"\n{'=' * 60}")
        print("🐷 DECISION CHECKPOINT")
        print(f"{'=' * 60}")
        print(f"Type: {params.type}")
        print(f"Summary: {params.summary}")
        print("Options:")
        for option in params.options:
            marker = " (recommended)" if option.id == params.recommended_option_id else ""
            print(f"- {option.id}: {option.label}{marker}")
            print(f"  Consequence: {option.consequence}")
            if option.message_to_send:
                print(f"  Message: {option.message_to_send}")
        print(f"{'=' * 60}")

        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: input("Choose an option id or type instructions: ").strip(),
            )
        except EOFError as e:
            raise RuntimeError(
                "Interactive input is not available. Run this command in the foreground "
                "so you can answer decision checkpoints."
            ) from e
        selected = self._coerce_checkpoint_response(params, response)
        self._record_event("decision_checkpoint_answered", selected)
        return json.dumps(selected)

    async def _decision_checkpoint_api(self, params: DecisionCheckpointParams) -> str:
        """API mode checkpoint with optional model-authored holding timeout."""
        self._pending_request = build_pending_request(params)
        self._record_event("decision_checkpoint_opened", self._pending_request)
        logger.info(
            "Waiting for decision checkpoint %s (%s)",
            params.checkpoint_id,
            params.type,
        )

        response_task = asyncio.create_task(self._response_queue.get())
        timeout_task: asyncio.Task | None = None
        if params.holding_message and params.holding_message_after_seconds:
            timeout_task = asyncio.create_task(
                asyncio.sleep(max(params.holding_message_after_seconds, 1))
            )

        tasks = [response_task]
        if timeout_task:
            tasks.append(timeout_task)
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()

        if timeout_task and timeout_task in done and not response_task.done():
            selected = holding_message_answer(params)
            self._record_event("decision_checkpoint_holding_message", selected)
        else:
            raw = response_task.result()
            selected = parse_answer(params, raw)
            self._record_event("decision_checkpoint_answered", selected)

        self._pending_request = None
        return json.dumps(selected)

    def _parse_checkpoint_response(
        self,
        params: DecisionCheckpointParams,
        raw: str,
    ) -> dict:
        return parse_answer(params, raw)

    def _coerce_checkpoint_response(
        self,
        params: DecisionCheckpointParams,
        response: str,
    ) -> dict:
        return coerce_answer(params, response)

    def provide_input(self, response: str) -> None:
        """Provide a response to a pending question."""
        self._response_queue.put_nowait(response)

    @property
    def pending_question(self) -> str | None:
        return self._pending_question

    @property
    def pending_request(self) -> dict | None:
        return self._pending_request

    @property
    def events(self) -> list[dict]:
        return list(self._events)

    def _record_event(self, event_type: str, payload: dict) -> None:
        self._events.append(
            {
                "event_type": event_type,
                "timestamp": datetime.now(UTC).isoformat(),
                **payload,
            }
        )


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
        "Pause for a structured user decision when the next step is consequential. "
        "Use this instead of ask_user for strategy pivots, offer choices, "
        "irreversible actions, verification choices, or timeout-risk moments. "
        "Provide explicit options and a recommended option. For any option that "
        "would send a customer-service message, include the exact message_to_send. "
        "For irreversible actions, the exact outbound message must be shown for "
        "user approval. If this returns selected_option_id='__holding_message__', "
        "send selected_message exactly as a neutral holding message, then call "
        "decision_checkpoint again with the same decision options.",
        param_model=DecisionCheckpointParams,
    )
    async def decision_checkpoint(params: DecisionCheckpointParams):
        if input_handler:
            response = await input_handler.decision_checkpoint(params)
            logger.info("User answered decision checkpoint: %s", params.checkpoint_id)
            return ActionResult(
                extracted_content=f"Decision checkpoint response: {response}",
                long_term_memory=f"Decision checkpoint {params.checkpoint_id}: {response}",
            )

        payload = params.model_dump()
        logger.info("Decision checkpoint needs input: %s", payload)
        return ActionResult(
            extracted_content=f"[DECISION_CHECKPOINT] {json.dumps(payload)}",
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
            long_term_memory=(f"Responder is {params.responder_type}. {next_step}"),
        )

    return tools
