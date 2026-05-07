from __future__ import annotations

import asyncio

import src.daemon.server as daemon_server
from fastapi.testclient import TestClient
from src.agent.result import TaskResult, TaskStatus


class FakeInputHandler:
    pending_question: str | None = None

    def provide_input(self, response: str) -> None:
        self.last_response = response


class FakeAgentBrain:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.input_handler = FakeInputHandler()
        self._step_log: list[dict] = []

    @property
    def step_log(self) -> list[dict]:
        return list(self._step_log)

    async def execute(self, **kwargs) -> TaskResult:
        self._step_log.append({
            "step": 1,
            "phase": "complete",
            "message": "fake agent is working",
        })
        await asyncio.sleep(0.2)
        return TaskResult(
            status=TaskStatus.SUCCESS,
            summary="fake run completed",
            steps_taken=1,
            duration_seconds=0.2,
        )


def reset_run_manager() -> None:
    daemon_server.run_manager = daemon_server.RunManager()


def test_agent_run_survives_side_panel_disconnect(monkeypatch):
    reset_run_manager()
    monkeypatch.setattr(daemon_server, "AgentBrain", FakeAgentBrain)
    app = daemon_server.create_app()

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "ready"
            assert ws.receive_json()["status"] == "idle"
            ws.send_json({
                "type": "start",
                "site": "amex",
                "url": "https://www.americanexpress.com/us/customer-service/",
                "task": "test run",
                "template": "general",
                "max_steps": 1,
            })
            assert ws.receive_json()["type"] == "status"
            state = ws.receive_json()
            assert state["type"] == "state"
            assert state["running"] is True

        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "ready"
            state = ws.receive_json()
            assert state["type"] == "state"
            assert state["status"] in {"starting", "running", "success"}
            assert state["status"] != "idle"

            while state["status"] != "success":
                message = ws.receive_json()
                if message.get("type") == "state":
                    state = message

            assert state["running"] is False
            assert state["message"] == "fake run completed"
