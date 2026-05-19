from __future__ import annotations

import asyncio
import time

import src.daemon.server as daemon_server
from fastapi.testclient import TestClient
from src.agent.result import TaskResult, TaskStatus
from src.daemon.run_session import progress_message


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
        self._step_log.append(
            {
                "step": 1,
                "phase": "complete",
                "message": "fake agent is working",
            }
        )
        await asyncio.sleep(0.2)
        return TaskResult(
            status=TaskStatus.SUCCESS,
            summary="fake run completed",
            steps_taken=1,
            duration_seconds=0.2,
        )


class FakeCheckpointInputHandler:
    def __init__(self):
        self.pending_request = None
        self.last_response = None

    def provide_input(self, response: str) -> None:
        self.last_response = response
        self.pending_request = None


class FakeCheckpointAgentBrain:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.input_handler = FakeCheckpointInputHandler()
        self._step_log: list[dict] = []

    @property
    def step_log(self) -> list[dict]:
        return list(self._step_log)

    async def execute(self, **kwargs) -> TaskResult:
        self.input_handler.pending_request = {
            "type": "decision_checkpoint",
            "checkpoint": {
                "checkpoint_id": "cp_daemon",
                "type": "strategy_pivot",
                "summary": "No retention offer is available.",
                "recommended_option_id": "close_card",
                "options": [
                    {
                        "id": "close_card",
                        "label": "Close card",
                        "consequence": "Proceed to disclosure.",
                        "message_to_send": "I would like to proceed toward closing.",
                    }
                ],
            },
        }
        for _ in range(40):
            if self.input_handler.last_response:
                break
            await asyncio.sleep(0.05)
        return TaskResult(
            status=TaskStatus.SUCCESS,
            summary=self.input_handler.last_response or "no answer",
            steps_taken=1,
            duration_seconds=0.2,
        )


def reset_run_manager() -> None:
    daemon_server.run_manager = daemon_server.RunManager()


def test_agent_run_survives_dashboard_disconnect(monkeypatch):
    reset_run_manager()
    monkeypatch.setattr(daemon_server, "AgentBrain", FakeAgentBrain)
    app = daemon_server.create_app()

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "ready"
            assert ws.receive_json()["status"] == "idle"
            ws.send_json(
                {
                    "type": "start",
                    "site": "amex",
                    "url": "https://www.americanexpress.com/us/customer-service/",
                    "task": "test run",
                    "template": "general",
                    "max_steps": 1,
                }
            )
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


def test_browser_launch_endpoint_uses_site_adapter(monkeypatch):
    reset_run_manager()
    launched = {}

    def fake_launch(config):
        launched["config"] = config
        return "http://127.0.0.1:9222"

    monkeypatch.setattr(daemon_server, "launch_cdp_chrome", fake_launch)
    app = daemon_server.create_app()

    with TestClient(app) as client:
        response = client.post("/browser/launch", json={"site": "amex"})

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["cdp_url"] == "http://127.0.0.1:9222"
    assert launched["config"].chrome_profile == "dedicated"
    assert launched["config"].disable_extensions is True
    assert "americanexpress.com" in launched["config"].initial_url


def test_daemon_lists_site_metadata():
    reset_run_manager()
    app = daemon_server.create_app()

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "ready"
            assert ws.receive_json()["status"] == "idle"
            ws.send_json({"type": "list_sites"})
            message = ws.receive_json()

    assert message["type"] == "sites"
    by_id = {item["id"]: item for item in message["items"]}
    assert by_id["oura"]["label"] == "Oura Ring"
    assert "support.ouraring.com" in by_id["oura"]["chat_url"]
    assert by_id["generic"]["chat_url"] == ""


def test_browser_launch_endpoint_supports_generic_current_tab(monkeypatch):
    reset_run_manager()
    launched = {}

    def fake_launch(config):
        launched["config"] = config
        return "http://127.0.0.1:9222"

    monkeypatch.setattr(daemon_server, "launch_cdp_chrome", fake_launch)
    app = daemon_server.create_app()

    with TestClient(app) as client:
        response = client.post("/browser/launch", json={"site": "generic"})

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert launched["config"].initial_url == "about:blank"


def test_browser_launch_endpoint_defaults_to_generic_blank_page(monkeypatch):
    reset_run_manager()
    launched = {}

    def fake_launch(config):
        launched["config"] = config
        return "http://127.0.0.1:9222"

    monkeypatch.setattr(daemon_server, "launch_cdp_chrome", fake_launch)
    app = daemon_server.create_app()

    with TestClient(app) as client:
        response = client.post("/browser/launch", json={})

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert launched["config"].initial_url == "about:blank"


def test_browser_status_endpoint_reports_debugger_state(monkeypatch):
    reset_run_manager()
    monkeypatch.setattr(daemon_server, "debugger_is_ready", lambda port: port == 9222)
    monkeypatch.setattr(
        daemon_server,
        "debugger_page_info",
        lambda port: {"url": "https://support.example/chat", "title": "Support"}
        if port == 9222
        else None,
    )
    app = daemon_server.create_app()

    with TestClient(app) as client:
        connected = client.get("/browser/status?cdp_url=http://127.0.0.1:9222")
        disconnected = client.get("/browser/status?cdp_url=http://127.0.0.1:9333")

    assert connected.status_code == 200
    assert connected.json()["connected"] is True
    assert connected.json()["cdp_url"] == "http://127.0.0.1:9222"
    assert connected.json()["current_url"] == "https://support.example/chat"
    assert connected.json()["current_title"] == "Support"
    assert disconnected.json()["connected"] is False


def test_daemon_broadcasts_and_answers_decision_checkpoint(monkeypatch):
    reset_run_manager()
    monkeypatch.setattr(daemon_server, "AgentBrain", FakeCheckpointAgentBrain)
    app = daemon_server.create_app()

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "ready"
            assert ws.receive_json()["status"] == "idle"
            ws.send_json(
                {
                    "type": "start",
                    "site": "amex",
                    "url": "https://www.americanexpress.com/us/customer-service/",
                    "task": "test checkpoint",
                    "template": "general",
                    "max_steps": 1,
                }
            )

            checkpoint = None
            for _ in range(20):
                message = ws.receive_json()
                if message.get("type") == "decision_checkpoint":
                    checkpoint = message["checkpoint"]
                    break

            assert checkpoint is not None
            assert checkpoint["checkpoint_id"] == "cp_daemon"
            assert checkpoint["options"][0]["message_to_send"]

            ws.send_json(
                {
                    "type": "answer",
                    "payload": {
                        "checkpoint_id": "cp_daemon",
                        "selected_option_id": "close_card",
                        "selected_message": "I would like to proceed toward closing.",
                    },
                }
            )

            result = None
            for _ in range(20):
                message = ws.receive_json()
                if message.get("type") == "result":
                    result = message
                    break

            assert result is not None
            assert '"selected_option_id": "close_card"' in result["summary"]


def test_daemon_snapshot_preserves_pending_decision_checkpoint(monkeypatch):
    reset_run_manager()
    monkeypatch.setattr(daemon_server, "AgentBrain", FakeCheckpointAgentBrain)
    app = daemon_server.create_app()

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "ready"
            assert ws.receive_json()["status"] == "idle"
            ws.send_json(
                {
                    "type": "start",
                    "site": "amex",
                    "url": "https://www.americanexpress.com/us/customer-service/",
                    "task": "test checkpoint",
                    "template": "general",
                    "max_steps": 1,
                }
            )

            checkpoint = None
            for _ in range(20):
                message = ws.receive_json()
                if message.get("type") == "decision_checkpoint":
                    checkpoint = message["checkpoint"]
                    break
            assert checkpoint is not None

        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "ready"
            state = ws.receive_json()

            assert state["type"] == "state"
            assert state["needs_input"] is True
            assert state["pending_request"]["type"] == "decision_checkpoint"
            assert state["pending_request"]["checkpoint"]["checkpoint_id"] == "cp_daemon"

            ws.send_json(
                {
                    "type": "answer",
                    "payload": {
                        "checkpoint_id": "cp_daemon",
                        "selected_option_id": "close_card",
                        "selected_message": "I would like to proceed toward closing.",
                    },
                }
            )

            result = None
            for _ in range(20):
                message = ws.receive_json()
                if message.get("type") == "result":
                    result = message
                    break
            assert result is not None


def test_rest_run_endpoints_answer_pending_decision_checkpoint(monkeypatch):
    reset_run_manager()
    monkeypatch.setattr(daemon_server, "AgentBrain", FakeCheckpointAgentBrain)
    app = daemon_server.create_app()

    with TestClient(app) as client:
        start = client.post(
            "/run/start",
            json={
                "site": "amex",
                "url": "https://www.americanexpress.com/us/customer-service/",
                "task": "test checkpoint",
                "template": "general",
                "max_steps": 1,
            },
        )
        assert start.status_code == 200
        assert start.json()["running"] is True

        state = None
        for _ in range(20):
            response = client.get("/run/state")
            assert response.status_code == 200
            state = response.json()
            if state["needs_input"]:
                break

            time.sleep(0.05)

        assert state is not None
        assert state["pending_request"]["type"] == "decision_checkpoint"
        assert state["pending_request"]["checkpoint"]["checkpoint_id"] == "cp_daemon"

        answer = client.post(
            "/run/answer",
            json={
                "payload": {
                    "checkpoint_id": "cp_daemon",
                    "selected_option_id": "close_card",
                    "selected_message": "I would like to proceed toward closing.",
                }
            },
        )
        assert answer.status_code == 200
        assert answer.json()["needs_input"] is False
        assert answer.json()["message"] == "Answer received. Continuing the run."

        result = None
        for _ in range(20):
            response = client.get("/run/state")
            assert response.status_code == 200
            result = response.json()
            if result["status"] == "success":
                break

            time.sleep(0.05)

        assert result is not None
        assert result["status"] == "success"
        assert '"selected_option_id": "close_card"' in result["message"]


def test_progress_message_prefers_specific_goal_and_filters_step_noise():
    assert (
        progress_message(
            {
                "step": 7,
                "phase": "complete",
                "message": "Step 7 complete",
                "goal": "Open the order-specific support page.",
            }
        )
        == "Open the order-specific support page."
    )
    assert progress_message({"step": 8, "phase": "starting", "message": "Step 8 started"}) == (
        "Checking the current page and chat state before the next action."
    )
    assert (
        progress_message(
            {"step": 9, "phase": "complete", "message": "Waiting"},
            {
                "type": "decision_checkpoint",
                "checkpoint": {"summary": "Choose refund method."},
            },
        )
        == "Choose refund method."
    )
