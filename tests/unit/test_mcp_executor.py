from __future__ import annotations

import json
from pathlib import Path

import pytest
from src.agent.mcp_executor import McpAgentAction, McpBrowserExecutor
from src.agent.result import TaskStatus
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
