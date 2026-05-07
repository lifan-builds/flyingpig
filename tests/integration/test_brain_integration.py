"""Integration tests for the agent brain and task execution pipeline."""

import pytest
from src.agent.brain import (
    AgentBrain,
    TaskStatus,
    UserInputHandler,
    _build_tools,
)
from src.agent.navigator import ChatNavigator
from src.sites.amex import AmexAdapter


class TestUserInputHandler:
    def test_cli_mode_creation(self):
        handler = UserInputHandler(mode="cli")
        assert handler.mode == "cli"
        assert handler.pending_question is None

    def test_api_mode_creation(self):
        handler = UserInputHandler(mode="api")
        assert handler.mode == "api"
        assert handler.pending_question is None

    @pytest.mark.asyncio
    async def test_api_mode_provide_input(self):
        handler = UserInputHandler(mode="api")

        # Simulate providing input
        handler.provide_input("test response")
        response = await handler._response_queue.get()
        assert response == "test response"


class TestNavigatorLoginFlow:
    @pytest.mark.asyncio
    async def test_open_chat_focuses_target_url_on_cdp_attach(self, monkeypatch):
        events = {}

        class FakeSession:
            def __init__(self, cdp_url=None):
                events["cdp_url"] = cdp_url

            async def start(self):
                events["started"] = True

            async def get_target_id_from_url(self, url):
                events["target_lookup"] = url
                return "target-123"

            async def on_SwitchTabEvent(self, event):  # noqa: N802
                events["switched_to"] = event.target_id

            async def get_current_page(self):
                return object()

            async def get_current_page_url(self):
                return "http://127.0.0.1:8086/?logged_in=true"

        monkeypatch.setattr("src.agent.navigator.BrowserSession", FakeSession)

        navigator = ChatNavigator(
            site_adapter=AmexAdapter(),
            cdp_url="http://127.0.0.1:9335",
            target_url="http://127.0.0.1:8086/?logged_in=true",
        )

        session = await navigator.open_chat()

        assert isinstance(session, FakeSession)
        assert events == {
            "cdp_url": "http://127.0.0.1:9335",
            "started": True,
            "target_lookup": "http://127.0.0.1:8086/?logged_in=true",
            "switched_to": "target-123",
        }

    @pytest.mark.asyncio
    async def test_wait_for_login_skips_controlled_browser_mode(self):
        class FakePage:
            def __init__(self):
                self.current_url = "https://www.americanexpress.com/en-us/account/login"
                self.goto_urls = []

            async def get_url(self):
                return self.current_url

            async def goto(self, url):
                self.goto_urls.append(url)
                self.current_url = url

        class FakeSession:
            def __init__(self):
                self.page = FakePage()

            async def get_current_page(self):
                return self.page

        navigator = ChatNavigator(site_adapter=AmexAdapter(), headless=True)
        navigator._session = FakeSession()
        input_handler = UserInputHandler(mode="api")

        await navigator.wait_for_login(input_handler)

        assert input_handler.pending_question is None
        assert navigator._session.page.goto_urls == []


class TestBuildTools:
    def test_build_tools_without_handler(self):
        tools = _build_tools()
        assert tools is not None

    def test_build_tools_with_handler(self):
        handler = UserInputHandler(mode="api")
        tools = _build_tools(handler)
        assert tools is not None

    def test_custom_actions_registered(self):
        tools = _build_tools()
        action_names = list(tools.registry.registry.actions.keys())
        assert "ask_user" in action_names
        assert "report_outcome" in action_names
        assert "report_detection" in action_names


class TestAgentBrain:
    def test_create_brain_amex(self):
        brain = AgentBrain(site="amex", headless=True)
        assert brain.site_adapter.name == "American Express"
        assert brain.headless is True

    def test_create_brain_with_model(self):
        brain = AgentBrain(site="amex", model="claude-opus")
        assert brain._model_name == "claude-opus"

    def test_create_brain_with_target_url(self):
        brain = AgentBrain(
            site="amex",
            cdp_url="http://127.0.0.1:9222",
            target_url="http://127.0.0.1:8086/?logged_in=true",
        )

        assert brain.target_url == "http://127.0.0.1:8086/?logged_in=true"

    def test_create_brain_with_cliproxyapi(self, monkeypatch):
        captured = {}

        class FakeChatOpenAI:
            def __init__(self, **kwargs):
                captured.update(kwargs)

        monkeypatch.setattr("src.agent.llm_runtime.ChatOpenAI", FakeChatOpenAI)
        monkeypatch.setattr(
            "src.agent.llm_runtime.settings.cliproxyapi_api_key",
            "sk-local-test-key",
        )
        monkeypatch.setattr(
            "src.agent.llm_runtime.settings.cliproxyapi_base_url",
            "http://127.0.0.1:8317/v1",
        )
        monkeypatch.setattr("src.agent.llm_runtime.settings.cliproxyapi_model", "gpt-5.5")

        brain = AgentBrain(site="amex", model="cliproxyapi")

        assert isinstance(brain.llm, FakeChatOpenAI)
        assert captured == {
            "model": "gpt-5.5",
            "api_key": "sk-local-test-key",
            "base_url": "http://127.0.0.1:8317/v1",
        }

    def test_extract_result_uses_agent_success_flag(self):
        class FakeHistory:
            def final_result(self):
                return "Task not completed."

            def number_of_steps(self):
                return 1

            def total_duration_seconds(self):
                return 2.0

            def agent_steps(self):
                return []

            def is_successful(self):
                return False

        brain = AgentBrain(site="amex", model="cliproxyapi")

        result = brain._extract_result(FakeHistory())

        assert result.status == TaskStatus.FAILED
        assert result.summary == "Task not completed."

    def test_create_brain_invalid_site(self):
        with pytest.raises(ValueError, match="Unknown site"):
            AgentBrain(site="nonexistent")

    @pytest.mark.asyncio
    async def test_dry_run_returns_success(self):
        brain = AgentBrain(site="amex", headless=True)
        result = await brain.execute(
            task="negotiate my annual fee",
            dry_run=True,
        )
        assert result.status == TaskStatus.SUCCESS
        assert "[DRY RUN]" in result.summary
        assert "American Express" in result.summary

    @pytest.mark.asyncio
    async def test_dry_run_with_template(self):
        brain = AgentBrain(site="amex", headless=True)
        result = await brain.execute(
            task="negotiate my annual fee",
            dry_run=True,
            template_id="negotiate_fee",
        )
        assert result.status == TaskStatus.SUCCESS
        assert result.outcome_details["template"] == "negotiate_fee"
        # Prompt should be longer with template
        assert result.outcome_details["prompt_length"] > 500

    @pytest.mark.asyncio
    async def test_dry_run_prompt_preview(self):
        brain = AgentBrain(site="amex", headless=True)
        result = await brain.execute(
            task="dispute a $50 charge",
            dry_run=True,
            template_id="dispute_charge",
        )
        assert "prompt_preview" in result.outcome_details
        assert len(result.outcome_details["prompt_preview"]) > 0
