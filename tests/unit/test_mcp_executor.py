from __future__ import annotations

import json
from pathlib import Path

import pytest
from src.agent.chrome_devtools_mcp import ChromeDevtoolsMcpError
from src.agent.mcp_executor import McpAgentAction, McpBrowserExecutor
from src.agent.result import TaskStatus
from src.agent.run_authorization import RunAuthorization
from src.agent.user_input import UserInputHandler


class FakeMcpSession:
    def __init__(self):
        self.selected = None
        self.calls = []
        self.snapshots = 0

    def select_page(self, page):
        self.selected = page
        return {"snapshot_text": "button uid=send Send"}

    def list_tools(self):
        return [
            {"name": "take_snapshot"},
            {"name": "click"},
            {"name": "fill"},
            {"name": "fill_form"},
            {"name": "type_text"},
            {"name": "press_key"},
            {"name": "wait_for"},
        ]

    def take_snapshot(self):
        self.snapshots += 1
        return {"snapshot_text": f"snapshot {self.snapshots} button uid=send Send"}

    def call_tool(self, name, args=None):
        self.calls.append((name, args or {}))
        return {"content": [{"type": "text", "text": f"called {name}"}]}


@pytest.mark.asyncio
async def test_mcp_executor_runs_browser_action_then_reports_outcome(tmp_path: Path):
    session = FakeMcpSession()
    actions = iter(
        [
            McpAgentAction(action="click", uid="send", thought="click send"),
            McpAgentAction(action="report_outcome", outcome="Done", thought="finished"),
        ]
    )

    async def planner(prompt):
        return next(actions)

    executor = McpBrowserExecutor(session_factory=lambda: session)
    result = await executor.run(
        task_prompt="Help with a mock support chat.",
        llm=planner,
        page={"index": 1, "url": "http://127.0.0.1/mock"},
        input_handler=UserInputHandler(mode="api"),
        max_steps=3,
        save_dir=tmp_path,
    )

    assert result.status == TaskStatus.SUCCESS
    assert result.summary == "Done"
    assert session.selected["index"] == 1
    assert session.calls == [("click", {"uid": "send", "includeSnapshot": False})]
    assert session.snapshots >= 2
    assert result.transcript_path
    artifact = json.loads(Path(result.transcript_path).read_text())
    assert artifact["backend"] == "mcp"


@pytest.mark.asyncio
async def test_mcp_executor_rejects_unknown_action(tmp_path: Path):
    async def planner(prompt):
        return McpAgentAction(action="evaluate_script", thought="unsafe")

    result = await McpBrowserExecutor(session_factory=FakeMcpSession).run(
        task_prompt="Task",
        llm=planner,
        page={"index": 1},
        input_handler=UserInputHandler(mode="api"),
        max_steps=1,
        save_dir=tmp_path,
    )

    assert result.status == TaskStatus.FAILED
    assert "unsupported action" in result.summary


@pytest.mark.asyncio
async def test_mcp_executor_recovers_from_provider_trailing_json(tmp_path: Path):
    class TrailingJsonLlm:
        def __init__(self):
            self.calls = 0

        async def ainvoke(self, messages, output_format=None):
            self.calls += 1
            if output_format is not None:
                raise RuntimeError("Invalid JSON: trailing characters [type=json_invalid]")
            return type(
                "Completion",
                (),
                {
                    "completion": (
                        '{"action":"report_outcome","outcome":"Recovered"} trailing explanation'
                    )
                },
            )()

    llm = TrailingJsonLlm()
    result = await McpBrowserExecutor(session_factory=FakeMcpSession).run(
        task_prompt="Task",
        llm=llm,
        page={"index": 1},
        input_handler=UserInputHandler(mode="api"),
        max_steps=1,
        save_dir=tmp_path,
    )

    assert result.status == TaskStatus.SUCCESS
    assert result.summary == "Recovered"
    assert llm.calls == 2


@pytest.mark.asyncio
async def test_mcp_executor_ask_user_delegates_to_input_handler(tmp_path: Path):
    actions = iter(
        [
            McpAgentAction(action="ask_user", question="Need code?", reason="verification"),
            McpAgentAction(action="report_outcome", outcome="Resumed"),
        ]
    )

    async def planner(prompt):
        return next(actions)

    handler = UserInputHandler(mode="api")

    async def answer_later():
        while handler.pending_question is None:
            await __import__("asyncio").sleep(0.01)
        handler.provide_input("123456")

    import asyncio

    task = asyncio.create_task(answer_later())
    result = await McpBrowserExecutor(session_factory=FakeMcpSession).run(
        task_prompt="Task",
        llm=planner,
        page={"index": 1},
        input_handler=handler,
        max_steps=3,
        save_dir=tmp_path,
    )
    await task

    assert result.status == TaskStatus.SUCCESS
    assert handler.events[0]["event_type"] == "question_opened"
    assert handler.events[1]["event_type"] == "question_answered"


@pytest.mark.asyncio
async def test_mcp_executor_maps_mcp_tool_arguments(tmp_path: Path):
    session = FakeMcpSession()
    actions = iter(
        [
            McpAgentAction(action="fill", uid="field", value="hello"),
            McpAgentAction(action="fill_form", fields=[{"uid": "a", "value": "one"}]),
            McpAgentAction(action="type_text", text="typed"),
            McpAgentAction(action="press_key", key="Enter"),
            McpAgentAction(action="wait_for", text="Done", timeout=5000),
            McpAgentAction(action="report_outcome", outcome="Mapped"),
        ]
    )

    async def planner(prompt):
        return next(actions)

    result = await McpBrowserExecutor(session_factory=lambda: session).run(
        task_prompt="Task",
        llm=planner,
        page={"index": 1},
        input_handler=UserInputHandler(mode="api"),
        max_steps=6,
        save_dir=tmp_path,
    )

    assert result.status == TaskStatus.SUCCESS
    assert session.calls == [
        ("fill", {"uid": "field", "value": "hello", "includeSnapshot": False}),
        ("fill_form", {"elements": [{"uid": "a", "value": "one"}], "includeSnapshot": False}),
        ("type_text", {"text": "typed"}),
        ("press_key", {"key": "Enter", "includeSnapshot": False}),
        ("wait_for", {"text": ["Done"], "timeout": 5000}),
    ]


@pytest.mark.asyncio
async def test_mcp_executor_continues_after_stale_element(tmp_path: Path):
    class StaleElementSession(FakeMcpSession):
        def call_tool(self, name, args=None):
            self.calls.append((name, args or {}))
            if name == "click":
                raise ChromeDevtoolsMcpError(
                    "Error: Element with uid 5_9 no longer exists on the page."
                )
            return {"content": [{"type": "text", "text": f"called {name}"}]}

    session = StaleElementSession()
    actions = iter(
        [
            McpAgentAction(action="click", uid="5_9"),
            McpAgentAction(action="report_outcome", outcome="Recovered"),
        ]
    )

    async def planner(prompt):
        return next(actions)

    executor = McpBrowserExecutor(session_factory=lambda: session)
    result = await executor.run(
        task_prompt="Task",
        llm=planner,
        page={"index": 1},
        input_handler=UserInputHandler(mode="api"),
        max_steps=2,
        save_dir=tmp_path,
    )

    assert result.status == TaskStatus.SUCCESS
    assert result.summary == "Recovered"
    assert "Page changed before the browser action completed" in executor.action_log[0]["result"]
    assert session.snapshots >= 2


@pytest.mark.asyncio
async def test_mcp_executor_continues_after_wait_timeout(tmp_path: Path):
    class WaitTimeoutSession(FakeMcpSession):
        def call_tool(self, name, args=None):
            self.calls.append((name, args or {}))
            if name == "wait_for":
                raise ChromeDevtoolsMcpError("Error: Timed out after waiting 5000ms")
            return {"content": [{"type": "text", "text": f"called {name}"}]}

    session = WaitTimeoutSession()
    actions = iter(
        [
            McpAgentAction(action="wait_for", text="Chat", timeout=5000),
            McpAgentAction(action="report_outcome", outcome="Recovered"),
        ]
    )

    async def planner(prompt):
        return next(actions)

    executor = McpBrowserExecutor(session_factory=lambda: session)
    result = await executor.run(
        task_prompt="Task",
        llm=planner,
        page={"index": 1},
        input_handler=UserInputHandler(mode="api"),
        max_steps=2,
        save_dir=tmp_path,
    )

    assert result.status == TaskStatus.SUCCESS
    assert result.summary == "Recovered"
    assert "Wait timed out without a match" in executor.action_log[0]["result"]
    assert session.snapshots >= 2


@pytest.mark.asyncio
async def test_mcp_executor_handles_textless_wait_without_mcp_call(tmp_path: Path, monkeypatch):
    session = FakeMcpSession()
    actions = iter(
        [
            McpAgentAction(action="wait_for", timeout=1000),
            McpAgentAction(action="report_outcome", outcome="Waited"),
        ]
    )
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    async def planner(prompt):
        return next(actions)

    monkeypatch.setattr("src.agent.mcp_executor.asyncio.sleep", fake_sleep)
    result = await McpBrowserExecutor(session_factory=lambda: session).run(
        task_prompt="Task",
        llm=planner,
        page={"index": 1},
        input_handler=UserInputHandler(mode="api"),
        max_steps=2,
        save_dir=tmp_path,
    )

    assert result.status == TaskStatus.SUCCESS
    assert sleeps == [1.0]
    assert session.calls == []


@pytest.mark.asyncio
async def test_mcp_executor_failure_writes_artifact(tmp_path: Path):
    async def planner(prompt):
        return McpAgentAction(action="evaluate_script", thought="unsafe")

    result = await McpBrowserExecutor(session_factory=FakeMcpSession).run(
        task_prompt="Task",
        llm=planner,
        page={"index": 1},
        input_handler=UserInputHandler(mode="api"),
        max_steps=1,
        save_dir=tmp_path,
    )

    assert result.status == TaskStatus.FAILED
    assert result.transcript_path
    artifact = json.loads(Path(result.transcript_path).read_text())
    assert artifact["outcome"]["error"] == result.summary


@pytest.mark.asyncio
async def test_send_chat_message_replaces_verifies_and_deduplicates(tmp_path: Path):
    class ChatSession(FakeMcpSession):
        def __init__(self):
            super().__init__()
            self.draft = "old appended draft"
            self.messages = []

        def take_snapshot(self):
            transcript = "\n".join(
                f'uid=1_{index} StaticText "{message}"'
                for index, message in enumerate(self.messages)
            )
            return {
                "snapshot_text": (
                    f"{transcript}\n"
                    f'uid=2_0 textbox "Type a message..." value="{self.draft}"\n'
                    'uid=2_1 button "send your message"'
                )
            }

        def call_tool(self, name, args=None):
            args = args or {}
            self.calls.append((name, args))
            if name == "fill":
                self.draft = args["value"]
            elif name == "click":
                self.messages.append(self.draft)
                self.draft = ""
            return {"content": [{"type": "text", "text": f"called {name}"}]}

    session = ChatSession()
    message = "Please close only the authorized card."
    actions = iter(
        [
            McpAgentAction(action="send_chat_message", text=message),
            McpAgentAction(action="send_chat_message", text=message),
            McpAgentAction(action="report_outcome", outcome="Done"),
        ]
    )

    async def planner(prompt):
        return next(actions)

    executor = McpBrowserExecutor(session_factory=lambda: session)
    result = await executor.run(
        task_prompt="Task",
        llm=planner,
        page={"index": 1},
        input_handler=UserInputHandler(mode="api"),
        max_steps=3,
        save_dir=tmp_path,
    )

    assert result.status == TaskStatus.SUCCESS
    assert session.messages == [message]
    assert [name for name, _ in session.calls].count("click") == 1
    assert "Skipped duplicate" in executor.action_log[1]["result"]


@pytest.mark.asyncio
async def test_authorized_cancellation_consent_bypasses_planner(tmp_path: Path):
    class ConsentSession(FakeMcpSession):
        def __init__(self):
            super().__init__()
            self.draft = ""
            self.sent = []

        def take_snapshot(self):
            messages = [
                "Would you like to proceed with the Card Cancellation?",
                *self.sent,
            ]
            if self.sent:
                messages.append(
                    "Requested account has been invalidated successfully and "
                    "submitted for cancellation."
                )
            transcript = "\n".join(
                f'uid=1_{index} StaticText "{message}"' for index, message in enumerate(messages)
            )
            return {
                "snapshot_text": (
                    f"{transcript}\n"
                    f'uid=2_0 textbox "Type a message..." value="{self.draft}"\n'
                    'uid=2_1 button "send your message"'
                )
            }

        def call_tool(self, name, args=None):
            args = args or {}
            if name == "fill":
                self.draft = args["value"]
            elif name == "click":
                self.sent.append(self.draft)
                self.draft = ""
            return {"content": [{"type": "text", "text": f"called {name}"}]}

    session = ConsentSession()
    planner_calls = 0

    async def planner(prompt):
        nonlocal planner_calls
        planner_calls += 1
        return McpAgentAction(action="report_outcome", outcome="Closed")

    result = await McpBrowserExecutor(session_factory=lambda: session).run(
        task_prompt="Close the card.",
        llm=planner,
        page={"index": 1},
        input_handler=UserInputHandler(mode="api"),
        max_steps=2,
        save_dir=tmp_path,
        authorization=RunAuthorization(
            target_account="12345",
            authorized_actions=["close_card"],
            user_authorized=True,
        ),
    )

    assert result.status == TaskStatus.SUCCESS
    assert planner_calls == 1
    assert session.sent == [
        "Yes. I understand and consent. Please proceed with closing only the "
        "authorized card ending in 12345."
    ]
    assert result.outcome_details["completion_checklist"][0]["complete"] is True


@pytest.mark.asyncio
async def test_mcp_executor_uses_fallback_after_primary_model_failure(tmp_path: Path):
    class FailedLlm:
        async def ainvoke(self, messages, **kwargs):
            raise TimeoutError("primary stalled")

    class FallbackLlm:
        async def ainvoke(self, messages, **kwargs):
            return type(
                "Completion",
                (),
                {"completion": McpAgentAction(action="report_outcome", outcome="Fallback")},
            )()

    result = await McpBrowserExecutor(session_factory=FakeMcpSession).run(
        task_prompt="Task",
        llm=FailedLlm(),
        fallback_llm=FallbackLlm(),
        llm_timeout_seconds=1,
        page={"index": 1},
        input_handler=UserInputHandler(mode="api"),
        max_steps=1,
        save_dir=tmp_path,
    )

    assert result.status == TaskStatus.SUCCESS
    assert result.summary == "Fallback"


@pytest.mark.asyncio
async def test_mcp_executor_blocks_direct_chat_textbox_fill(tmp_path: Path):
    class ComposerSession(FakeMcpSession):
        def take_snapshot(self):
            return {
                "snapshot_text": (
                    'uid=2_0 textbox "Type a message..." focusable focused value=""\n'
                    'uid=2_1 button "send your message"'
                )
            }

    session = ComposerSession()
    actions = iter(
        [
            McpAgentAction(action="fill", uid="2_0", value="duplicate"),
            McpAgentAction(action="report_outcome", outcome="Stopped"),
        ]
    )

    async def planner(prompt):
        return next(actions)

    executor = McpBrowserExecutor(session_factory=lambda: session)
    result = await executor.run(
        task_prompt="Task",
        llm=planner,
        page={"index": 1},
        input_handler=UserInputHandler(mode="api"),
        max_steps=2,
        save_dir=tmp_path,
    )

    assert result.status == TaskStatus.SUCCESS
    assert session.calls == []
    assert "Use send_chat_message" in executor.action_log[0]["result"]
