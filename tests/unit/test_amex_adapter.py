"""Tests for the Amex site adapter and task templates."""

import pytest
from src.sites.amex import AmexAdapter
from src.sites.profiles import AMEX_PROFILE
from src.sites.task_templates import (
    get_template,
    get_templates,
    list_all_templates,
    load_prompt_template,
)


class TestAmexAdapter:
    def setup_method(self):
        self.adapter = AmexAdapter()

    def test_name(self):
        assert self.adapter.name == "American Express"

    def test_chat_url(self):
        assert "americanexpress.com" in self.adapter.chat_url
        assert "customer-service" in self.adapter.chat_url

    def test_login_url(self):
        assert "americanexpress.com" in self.adapter.login_url
        assert "login" in self.adapter.login_url

    def test_requires_login(self):
        assert self.adapter.requires_login is True

    def test_build_prompt_basic(self):
        prompt = self.adapter.build_task_prompt(
            user_task="Waive my annual fee",
            escalation_instructions="Try to reach a human",
            detection_instructions="Detect AI chatbots",
        )
        assert "Waive my annual fee" in prompt
        assert "Try to reach a human" in prompt
        assert "American Express" in prompt
        assert "ask_user" in prompt  # Should reference the ask_user tool

    def test_build_prompt_with_template(self):
        prompt = self.adapter.build_task_prompt(
            user_task="negotiate my annual fee",
            escalation_instructions="",
            detection_instructions="",
            template_id="negotiate_fee",
        )
        # Template should add specific negotiation tactics
        assert "annual fee" in prompt.lower()
        assert "retention" in prompt.lower() or "loyalty" in prompt.lower()

    def test_build_prompt_with_general_template(self):
        prompt = self.adapter.build_task_prompt(
            user_task="ask about travel insurance coverage",
            escalation_instructions="",
            detection_instructions="",
            template_id="general",
        )
        # General template should substitute {user_task}
        assert "ask about travel insurance coverage" in prompt

    def test_build_prompt_security_rules(self):
        prompt = self.adapter.build_task_prompt(
            user_task="test",
            escalation_instructions="",
            detection_instructions="",
        )
        assert "Never fabricate" in prompt
        assert "ask_user" in prompt
        assert "Use `decision_checkpoint` instead of `ask_user`" in prompt
        assert "{decision_checkpoint_instructions}" not in prompt

    def test_build_prompt_login_instructions(self):
        prompt = self.adapter.build_task_prompt(
            user_task="test",
            escalation_instructions="",
            detection_instructions="",
        )
        assert "login" in prompt.lower() or "logged in" in prompt.lower()

    def test_build_prompt_chat_finding(self):
        prompt = self.adapter.build_task_prompt(
            user_task="test",
            escalation_instructions="",
            detection_instructions="",
        )
        assert "Chat" in prompt  # Should mention finding the chat widget

    def test_escalation_keywords(self):
        keywords = self.adapter.get_known_escalation_keywords()
        assert "supervisor" in keywords
        assert "retention" in keywords
        assert "loyalty department" in keywords

    def test_declarative_amex_profile_supplies_adapter_data(self):
        assert self.adapter.name == AMEX_PROFILE.name
        assert self.adapter.chat_url == AMEX_PROFILE.chat_url
        assert self.adapter.requires_login == AMEX_PROFILE.requires_login

    def test_build_prompt_invalid_template(self):
        # Invalid template should fall back to user_task
        prompt = self.adapter.build_task_prompt(
            user_task="my actual task",
            escalation_instructions="",
            detection_instructions="",
            template_id="nonexistent_template",
        )
        assert "my actual task" in prompt


class TestTaskTemplates:
    def test_get_amex_templates(self):
        templates = get_templates("amex")
        assert len(templates) >= 4
        ids = [t.id for t in templates]
        assert "negotiate_fee" in ids
        assert "dispute_charge" in ids
        assert "retention_offer" in ids
        assert "general" in ids

    def test_get_templates_case_insensitive(self):
        templates = get_templates("AMEX")
        assert len(templates) >= 4

    def test_get_templates_unknown_site(self):
        templates = get_templates("nonexistent")
        assert templates == []

    def test_profile_site_uses_generic_templates(self):
        templates = get_templates("oura")
        ids = [t.id for t in templates]
        assert "general" in ids
        assert "retention_offer" in ids

    def test_get_specific_template(self):
        template = get_template("amex", "negotiate_fee")
        assert template is not None
        assert template.name == "Negotiate Annual Fee"
        assert template.site == "amex"

    def test_get_nonexistent_template(self):
        template = get_template("amex", "nonexistent")
        assert template is None

    def test_load_prompt_template(self):
        content = load_prompt_template("amex", "negotiate_fee.txt")
        assert "annual fee" in content.lower()
        assert len(content) > 100  # Should be substantial

    def test_load_prompt_template_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_prompt_template("amex", "nonexistent.txt")

    def test_all_prompt_files_exist(self):
        templates = get_templates("amex")
        for t in templates:
            content = load_prompt_template("amex", t.prompt_file)
            assert len(content) > 50, f"Template {t.id} prompt file is too short"

    def test_list_all_templates(self):
        all_templates = list_all_templates()
        assert "amex" in all_templates
        assert "oura" in all_templates
        assert len(all_templates["amex"]) >= 4

    def test_dispute_template_has_required_inputs(self):
        template = get_template("amex", "dispute_charge")
        assert template is not None
        assert "charge_amount" in template.required_inputs
        assert "merchant_name" in template.required_inputs

    def test_general_template_substitution(self):
        content = load_prompt_template("amex", "general.txt")
        assert "{user_task}" in content  # Placeholder should exist
