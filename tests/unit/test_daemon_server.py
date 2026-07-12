from __future__ import annotations

import asyncio
import time

import src.daemon.server as daemon_server
from fastapi.testclient import TestClient
from src.agent.result import TaskResult, TaskStatus
from src.daemon.follow_up_reminders import FollowUpReminderStore
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
            chat_transcript=["Human: I can help.", "Agent: Thank you."],
            transcript_path="recordings/fake.json",
            outcome_details={
                "human_reached": True,
                "amount_saved": "$10",
                "next_steps": "Watch for confirmation email.",
            },
            steps_taken=1,
            duration_seconds=0.2,
        )


class FakeWaitingRepAgentBrain:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.input_handler = FakeCheckpointInputHandler()
        self._step_log: list[dict] = []

    @property
    def step_log(self) -> list[dict]:
        return list(self._step_log)

    async def execute(self, **kwargs) -> TaskResult:
        self._step_log.append(
            {
                "step": 3,
                "phase": "complete",
                "message": "The representative said please wait while they are checking.",
            }
        )
        await asyncio.sleep(1.0)
        return TaskResult(
            status=TaskStatus.SUCCESS,
            summary="rep finished",
            steps_taken=3,
            duration_seconds=0.4,
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
            checkpoint_events=[
                {
                    "event_type": "decision_checkpoint_answered",
                    "checkpoint_id": "cp_daemon",
                    "selected_option_id": "close_card",
                    "selected_message": "I would like to proceed toward closing.",
                    "timestamp": "2026-05-21T00:00:00+00:00",
                }
            ],
            steps_taken=1,
            duration_seconds=0.2,
        )


class FakeManualLoginAgentBrain:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.input_handler = FakeCheckpointInputHandler()
        self._step_log: list[dict] = []

    @property
    def step_log(self) -> list[dict]:
        return list(self._step_log)

    async def execute(self, **kwargs) -> TaskResult:
        self.input_handler.pending_request = {
            "type": "question",
            "question": "Please log in in the visible browser, then tell Flying Pig to resume.",
            "reason": "Manual login is required before customer-service chat can continue.",
        }
        for _ in range(40):
            if self.input_handler.last_response:
                break
            await asyncio.sleep(0.05)
        return TaskResult(
            status=TaskStatus.SUCCESS,
            summary="login resumed",
            steps_taken=1,
            duration_seconds=0.2,
        )


class FakeHucaAgentBrain:
    tasks: list[str] = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.input_handler = FakeCheckpointInputHandler()
        self._step_log: list[dict] = []

    @property
    def step_log(self) -> list[dict]:
        return list(self._step_log)

    async def execute(self, **kwargs) -> TaskResult:
        task = kwargs["task"]
        self.__class__.tasks.append(task)
        if "HUCA recovery was explicitly requested" in task:
            return TaskResult(
                status=TaskStatus.SUCCESS,
                summary="HUCA restarted the task.",
                steps_taken=1,
                duration_seconds=0.1,
            )

        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            raise

        return TaskResult(
            status=TaskStatus.FAILED,
            summary="initial run should have been cancelled",
            steps_taken=1,
            duration_seconds=30,
        )


def reset_run_manager() -> None:
    daemon_server.run_manager = daemon_server.RunManager()
    FakeHucaAgentBrain.tasks = []


def run_payload(**overrides) -> dict:
    payload = {
        "site": "amex",
        "url": "https://www.americanexpress.com/us/customer-service/",
        "target_url": "https://www.americanexpress.com/us/customer-service/",
        "cdp_url": "http://127.0.0.1:9222",
        "task": "test run",
        "template": "general",
        "max_steps": 1,
        "permission_mode": "supervised_browser",
        "user_authorized": True,
        "evidence_capture": True,
        "login_expectation": "manual_visible_browser",
        "irreversible_actions_require_checkpoint": True,
    }
    payload.update(overrides)
    return payload


def test_agent_run_survives_dashboard_disconnect(monkeypatch):
    reset_run_manager()
    monkeypatch.setattr(daemon_server, "AgentBrain", FakeAgentBrain)
    app = daemon_server.create_app()

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "ready"
            assert ws.receive_json()["status"] == "ready_to_start"
            ws.send_json({"type": "start", **run_payload()})
            first = ws.receive_json()
            if first["type"] == "state":
                assert first["status"] == "preparing"
                first = ws.receive_json()
            while first["type"] != "status":
                first = ws.receive_json()
            assert first["type"] == "status"
            state = ws.receive_json()
            assert state["type"] == "state"
            assert state["running"] is True

        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "ready"
            state = ws.receive_json()
            assert state["type"] == "state"
            assert state["status"] in {"preparing", "running", "completed"}
            assert state["status"] != "ready_to_start"

            while state["status"] != "completed":
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
    assert response.json()["timing_span"]["name"] == "launch"
    assert launched["config"].chrome_profile == "dedicated"
    assert launched["config"].disable_extensions is True
    assert "americanexpress.com" in launched["config"].initial_url


def test_daemon_serves_localhost_dashboard():
    reset_run_manager()
    app = daemon_server.create_app()

    with TestClient(app) as client:
        root = client.get("/", follow_redirects=False)
        dashboard = client.get("/dashboard/")
        script = client.get("/dashboard/dashboard.js")

    assert root.status_code in {307, 308}
    assert root.headers["location"] == "/dashboard/"
    assert dashboard.status_code == 200
    assert "Flying Pig Dashboard" in dashboard.text
    assert script.status_code == 200
    assert "localStorage" in script.text


def test_daemon_lists_site_metadata():
    reset_run_manager()
    app = daemon_server.create_app()

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "ready"
            assert ws.receive_json()["status"] == "ready_to_start"
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


def test_browser_launch_endpoint_accepts_user_default_profile_option(monkeypatch):
    reset_run_manager()
    launched = {}

    def fake_launch(config):
        launched["config"] = config
        return "http://127.0.0.1:9222"

    monkeypatch.setattr(daemon_server, "launch_cdp_chrome", fake_launch)
    app = daemon_server.create_app()

    with TestClient(app) as client:
        response = client.post(
            "/browser/launch",
            json={"site": "generic", "chrome_profile": "existing"},
        )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert launched["config"].chrome_profile == "existing"


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
    monkeypatch.setattr(
        daemon_server,
        "debugger_is_ready",
        lambda *args, **kwargs: kwargs.get("cdp_url") == "http://localhost:9222",
    )
    monkeypatch.setattr(
        daemon_server,
        "debugger_page_info",
        lambda *args, **kwargs: {"url": "https://support.example/chat", "title": "Support"}
        if kwargs.get("cdp_url") == "http://localhost:9222"
        else None,
    )
    app = daemon_server.create_app()

    with TestClient(app) as client:
        connected = client.get("/browser/status?cdp_url=http://localhost:9222")
        disconnected = client.get("/browser/status?cdp_url=http://127.0.0.1:9333")

    assert connected.status_code == 200
    assert connected.json()["connected"] is True
    assert connected.json()["cdp_url"] == "http://localhost:9222"
    assert connected.json()["current_url"] == "https://support.example/chat"
    assert connected.json()["current_title"] == "Support"
    assert disconnected.json()["connected"] is False


def test_browser_attach_endpoint_preserves_existing_chrome_endpoint(monkeypatch):
    reset_run_manager()
    monkeypatch.setattr(
        daemon_server,
        "debugger_is_ready",
        lambda *args, **kwargs: kwargs.get("cdp_url") == "http://localhost:9335",
    )
    monkeypatch.setattr(
        daemon_server,
        "debugger_page_info",
        lambda *args, **kwargs: {"url": "https://example.com/support", "title": "Support"},
    )
    app = daemon_server.create_app()

    with TestClient(app) as client:
        response = client.post(
            "/browser/attach",
            json={"cdp_url": "localhost:9335"},
        )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["cdp_url"] == "http://localhost:9335"
    assert response.json()["current_url"] == "https://example.com/support"


def test_browser_attach_endpoint_reports_setup_help_when_unreachable(monkeypatch):
    reset_run_manager()
    monkeypatch.setattr(daemon_server, "debugger_is_ready", lambda *args, **kwargs: False)
    app = daemon_server.create_app()

    with TestClient(app) as client:
        response = client.post(
            "/browser/attach",
            json={"cdp_url": "http://[::1]:9222"},
        )

    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert response.json()["cdp_url"] == "http://[::1]:9222"
    assert "remote-debugging-port" in response.json()["error"]


class FakeMcpClient:
    pages = [
        {
            "index": 0,
            "id": "target-0",
            "title": "CPA Management Center",
            "url": "https://cpa.example/dashboard",
            "cdp_url": "http://localhost:9335",
        }
    ]

    def connect(self):
        return self.list_pages()

    def list_pages(self):
        return list(self.pages)

    def select_page(self, page):
        return {"page": page, "snapshot_text": "button Submit"}


def test_browser_mcp_connect_returns_existing_chrome_pages(monkeypatch):
    reset_run_manager()
    monkeypatch.setattr(daemon_server, "chrome_mcp_session", FakeMcpClient)
    app = daemon_server.create_app()

    with TestClient(app) as client:
        response = client.post("/browser/mcp/connect")

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["connected"] is True
    assert response.json()["pages"][0]["title"] == "CPA Management Center"


def test_browser_mcp_select_returns_cdp_handoff(monkeypatch):
    reset_run_manager()
    monkeypatch.setattr(daemon_server, "chrome_mcp_session", FakeMcpClient)
    app = daemon_server.create_app()

    with TestClient(app) as client:
        response = client.post(
            "/browser/mcp/select",
            json={"page_index": 0},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["browser_ready"] is True
    assert payload["cdp_url"] == "http://localhost:9335"
    assert payload["current_url"] == "https://cpa.example/dashboard"


def test_browser_mcp_connect_reports_remote_debugging_help(monkeypatch):
    reset_run_manager()

    class FailingMcpClient:
        def connect(self):
            raise daemon_server.ChromeDevtoolsMcpError(
                "Could not connect to Chrome. Could not find DevToolsActivePort"
            )

    monkeypatch.setattr(daemon_server, "chrome_mcp_session", FailingMcpClient)
    app = daemon_server.create_app()

    with TestClient(app) as client:
        response = client.post("/browser/mcp/connect")

    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert "chrome://inspect/#remote-debugging" in response.json()["message"]


def test_browser_mcp_select_claims_mcp_readiness_without_cdp(monkeypatch):
    reset_run_manager()

    class InspectOnlyMcpClient(FakeMcpClient):
        pages = [
            {
                "index": 0,
                "id": "target-0",
                "title": "Existing tab",
                "url": "https://example.com/support",
                "cdp_url": None,
            }
        ]

    monkeypatch.setattr(daemon_server, "chrome_mcp_session", InspectOnlyMcpClient)
    app = daemon_server.create_app()

    with TestClient(app) as client:
        response = client.post("/browser/mcp/select", json={"page_index": 0})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["browser_ready"] is True
    assert payload["browser_backend"] == "mcp"
    assert payload["cdp_url"] is None
    assert "MCP control" in payload["message"]


def test_run_start_accepts_mcp_backend_without_cdp(monkeypatch):
    reset_run_manager()
    captured = {}

    class FakeMcpAgentBrain(FakeAgentBrain):
        def __init__(self, **kwargs):
            captured.update(kwargs)
            super().__init__(**kwargs)

    monkeypatch.setattr(daemon_server, "AgentBrain", FakeMcpAgentBrain)
    app = daemon_server.create_app()

    payload = run_payload(
        cdp_url=None,
        browser_backend="mcp",
        mcp_page={"index": 1, "url": "https://example.com/support"},
        target_url="https://example.com/support",
        url="https://example.com/support",
        site="generic",
    )

    with TestClient(app) as client:
        response = client.post("/run/start", json=payload)

    assert response.status_code == 200
    assert response.json()["running"] is True
    assert captured["browser_backend"] == "mcp"
    assert captured["mcp_page"] == {"index": 1, "url": "https://example.com/support"}
    assert captured["cdp_url"] is None


    reset_run_manager()
    monkeypatch.setattr(daemon_server, "AgentBrain", FakeCheckpointAgentBrain)
    app = daemon_server.create_app()

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "ready"
            assert ws.receive_json()["status"] == "ready_to_start"
            ws.send_json({"type": "start", **run_payload(task="test checkpoint")})

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
                if message.get("type") == "result_ready":
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
            assert ws.receive_json()["status"] == "ready_to_start"
            ws.send_json({"type": "start", **run_payload(task="test checkpoint")})

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
            assert state["status"] == "checkpoint_pending"
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
                if message.get("type") == "result_ready":
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
            json=run_payload(task="test checkpoint"),
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
        assert state["status"] == "checkpoint_pending"
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
        for _ in range(80):
            response = client.get("/run/state")
            assert response.status_code == 200
            result = response.json()
            if result["status"] == "completed":
                break

            time.sleep(0.05)

        assert result is not None
        assert result["status"] == "completed"
        assert '"selected_option_id": "close_card"' in result["message"]


def test_huca_cancels_active_run_and_restarts_same_task(monkeypatch):
    reset_run_manager()
    monkeypatch.setattr(daemon_server, "AgentBrain", FakeHucaAgentBrain)
    app = daemon_server.create_app()

    with TestClient(app) as client:
        start = client.post(
            "/run/start",
            json=run_payload(task="Ask for a retention offer.", max_steps=80),
        )
        assert start.status_code == 200
        assert start.json()["running"] is True

        huca = client.post(
            "/run/huca",
            json=run_payload(task="Ask for a retention offer.", max_steps=80),
        )
        assert huca.status_code == 200
        assert huca.json()["running"] is True
        assert huca.json()["message"] == "Restarting fresh chat for amex"

        result = None
        for _ in range(20):
            response = client.get("/run/state")
            assert response.status_code == 200
            result = response.json()
            if result["status"] == "completed":
                break

            time.sleep(0.05)

        assert result is not None
        assert result["status"] == "completed"
        assert FakeHucaAgentBrain.tasks[0] == "Ask for a retention offer."
        assert "HUCA recovery was explicitly requested" in FakeHucaAgentBrain.tasks[1]
        assert "Ask for a retention offer." in FakeHucaAgentBrain.tasks[1]


def test_preflight_gate_failures_are_visible_without_starting_agent(monkeypatch):
    reset_run_manager()
    monkeypatch.setattr(daemon_server, "AgentBrain", FakeAgentBrain)
    app = daemon_server.create_app()

    with TestClient(app) as client:
        response = client.post(
            "/run/start",
            json=run_payload(
                task="Call support and use my password to cancel without asking.",
                user_authorized=False,
                cdp_url="",
                irreversible_actions_require_checkpoint=False,
            ),
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["running"] is False
    assert payload["status"] == "ready_to_start"
    codes = {item["code"] for item in payload["preflight_failures"]}
    assert "unsupported_scope" in codes
    assert "missing_user_authorization" in codes
    assert "missing_work_window" in codes
    assert "checkpoint_required" in codes


def test_follow_up_reminder_api_persists_and_cancels(tmp_path):
    reset_run_manager()
    store = FollowUpReminderStore(tmp_path / "reminders.json")
    app = daemon_server.create_app(reminder_store=store)

    with TestClient(app) as client:
        created = client.post(
            "/follow-up-reminders",
            json={
                "title": "Contact support",
                "message": "Request the remaining credit balance.",
                "due_at": "2026-07-14T16:00:00Z",
                "source": {"type": "contact_support_after_credit_posts"},
            },
        )
        reminder = created.json()["reminder"]
        listed = client.get("/follow-up-reminders").json()["items"]
        cancelled = client.delete(f"/follow-up-reminders/{reminder['id']}").json()

    assert created.status_code == 200
    assert listed[0]["id"] == reminder["id"]
    assert cancelled["ok"] is True
    assert cancelled["reminder"]["status"] == "cancelled"


def test_waiting_on_rep_state_snapshot_from_active_human_work(monkeypatch):
    reset_run_manager()
    monkeypatch.setattr(daemon_server, "AgentBrain", FakeWaitingRepAgentBrain)
    app = daemon_server.create_app()

    with TestClient(app) as client:
        start = client.post("/run/start", json=run_payload())
        assert start.status_code == 200

        state = None
        for _ in range(20):
            response = client.get("/run/state")
            assert response.status_code == 200
            state = response.json()
            if state["status"] == "waiting_on_rep":
                break
            time.sleep(0.05)

        assert state is not None
        assert state["status"] == "waiting_on_rep"
        assert "checking" in state["message"].lower()
        assert state["running"] is True


def test_manual_login_request_is_reconnect_safe(monkeypatch):
    reset_run_manager()
    monkeypatch.setattr(daemon_server, "AgentBrain", FakeManualLoginAgentBrain)
    app = daemon_server.create_app()

    with TestClient(app) as client:
        start = client.post("/run/start", json=run_payload())
        assert start.status_code == 200

        state = None
        for _ in range(20):
            response = client.get("/run/state")
            assert response.status_code == 200
            state = response.json()
            if state["needs_input"]:
                break
            time.sleep(0.05)

        assert state is not None
        assert state["status"] == "waiting_on_login"
        assert state["pending_request"]["type"] == "manual_login_required"
        assert "log in" in state["pending_request"]["question"].lower()

        answer = client.post("/run/answer", json={"text": "Logged in now."})
        assert answer.status_code == 200


def test_result_ready_payload_shape_from_daemon(monkeypatch):
    reset_run_manager()
    monkeypatch.setattr(daemon_server, "AgentBrain", FakeAgentBrain)
    app = daemon_server.create_app()

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "ready"
            assert ws.receive_json()["status"] == "ready_to_start"
            ws.send_json({"type": "start", **run_payload()})

            result = None
            for _ in range(20):
                message = ws.receive_json()
                if message.get("type") == "result_ready":
                    result = message
                    break

    assert result is not None
    assert result["outcome_summary"] == "fake run completed"
    assert result["evidence"]["transcript_path"] == "recordings/fake.json"
    assert result["evidence"]["chat_transcript_lines"] == 2
    assert result["human_reached"] is True
    assert result["offer_result"] == "$10"
    assert result["scorecard"]["site_profile"] == "amex"
    assert result["scorecard"]["goal_type"] == "general"
    assert result["scorecard"]["huca_attempts"] == 0
    assert result["scorecard"]["user_confirmed_outcome"] is None
    assert result["timing_summary"]["by_name_ms"]["preflight"] >= 0
    assert result["timing_summary"]["by_name_ms"]["agent_construction"] >= 0


def test_run_outcome_marks_current_scorecard(monkeypatch):
    reset_run_manager()
    monkeypatch.setattr(daemon_server, "AgentBrain", FakeAgentBrain)
    app = daemon_server.create_app()

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "ready"
            assert ws.receive_json()["status"] == "ready_to_start"
            ws.send_json({"type": "start", **run_payload()})

            result = None
            for _ in range(20):
                message = ws.receive_json()
                if message.get("type") == "result_ready":
                    result = message
                    break

        assert result is not None
        response = client.post("/run/outcome", json={"outcome": "solved"})

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["scorecard"]["user_confirmed_outcome"] == "solved"


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
        "Checking the page and support chat before acting."
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
