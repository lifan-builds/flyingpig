"""Tests for site adapter registry."""

import pytest
from src.sites.profile_adapter import ProfileBackedAdapter
from src.sites.registry import get_site_adapter, list_sites, resolve_from_url


class TestSiteRegistry:
    def test_get_amex_adapter(self):
        adapter = get_site_adapter("amex")
        assert adapter.name == "American Express"
        assert "americanexpress.com" in adapter.chat_url

    def test_case_insensitive(self):
        adapter = get_site_adapter("AMEX")
        assert adapter.name == "American Express"

    def test_unknown_site_raises(self):
        with pytest.raises(ValueError, match="Unknown site"):
            get_site_adapter("nonexistent")

    def test_list_sites(self):
        sites = list_sites()
        assert "amex" in sites
        assert "generic" in sites
        assert "oura" in sites

    def test_get_oura_profile_adapter(self):
        adapter = get_site_adapter("oura")
        assert isinstance(adapter, ProfileBackedAdapter)
        assert adapter.name == "Oura Ring"
        assert "support.ouraring.com" in adapter.chat_url

    def test_resolve_oura_from_url(self):
        site = resolve_from_url(
            "https://support.ouraring.com/hc/en-us/articles/360047222554-Contact-Us"
        )
        assert site == "oura"

    def test_unknown_url_resolves_to_generic(self):
        site = resolve_from_url("https://example.com/support")
        assert site == "generic"

    def test_adapter_builds_prompt(self):
        adapter = get_site_adapter("amex")
        prompt = adapter.build_task_prompt(
            user_task="Waive my annual fee",
            escalation_instructions="Try to reach a human",
            detection_instructions="Detect AI chatbots",
        )
        assert "Waive my annual fee" in prompt
        assert "Try to reach a human" in prompt
        assert "American Express" in prompt

    def test_amex_requires_login(self):
        adapter = get_site_adapter("amex")
        assert adapter.requires_login is True

    def test_amex_escalation_keywords(self):
        adapter = get_site_adapter("amex")
        keywords = adapter.get_known_escalation_keywords()
        assert "supervisor" in keywords
        assert "retention" in keywords

    def test_prompt_includes_security_rules(self):
        adapter = get_site_adapter("amex")
        prompt = adapter.build_task_prompt(
            user_task="test",
            escalation_instructions="",
            detection_instructions="",
        )
        assert "Never fabricate" in prompt
        assert "ask_user" in prompt  # Should reference ask_user tool for stopping

    def test_profile_prompt_includes_site_context_and_chat_surface_boundary(self):
        adapter = get_site_adapter("oura")
        prompt = adapter.build_task_prompt(
            user_task="ask about my ring warranty",
            escalation_instructions="Escalate when needed",
            detection_instructions="Detect bots",
            template_id="general",
        )
        assert "Known Site Profile: Oura Ring" in prompt
        assert "Finn" in prompt
        assert "live Oura expert" in prompt
        assert "Do not roam through menus" in prompt
        assert "ask about my ring warranty" in prompt

    def test_generic_prompt_does_not_force_redundant_goal_confirmation(self):
        adapter = get_site_adapter("generic")
        prompt = adapter.build_task_prompt(
            user_task="ask for a goodwill credit",
            escalation_instructions="Escalate when needed",
            detection_instructions="Detect bots",
        )

        assert "proceed without asking the user to confirm" in prompt
        assert "ask permission to send the exact request" in prompt
        assert "STOP and use `ask_user`" in prompt
        assert "bot-to-human transfer" in prompt
        assert "Confirm the user's goal" not in prompt
