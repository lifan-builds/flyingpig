"""Tests for site adapter registry."""

import pytest
from src.sites.registry import get_site_adapter, list_sites


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
