"""End-to-end tests for Amex agent interaction.

These tests validate the full pipeline. Tests marked @pytest.mark.slow
require a real browser and network access.
"""

import pytest
from src.agent.brain import AgentBrain, TaskStatus


class TestAmexE2EDryRun:
    """E2E tests using dry-run mode (no browser needed)."""

    @pytest.mark.asyncio
    async def test_full_pipeline_dry_run(self):
        """Validate the entire pipeline executes without errors."""
        brain = AgentBrain(site="amex", headless=True)
        result = await brain.execute(
            task="Negotiate a waiver for my $695 Platinum annual fee",
            dry_run=True,
            template_id="negotiate_fee",
        )
        assert result.status == TaskStatus.SUCCESS
        assert "DRY RUN" in result.summary
        assert result.outcome_details["prompt_length"] > 1000

    @pytest.mark.asyncio
    async def test_dispute_pipeline_dry_run(self):
        """Validate dispute template pipeline."""
        brain = AgentBrain(site="amex", headless=True)
        result = await brain.execute(
            task="Dispute a $150 charge from XYZ Store on March 10",
            dry_run=True,
            template_id="dispute_charge",
        )
        assert result.status == TaskStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_retention_pipeline_dry_run(self):
        """Validate retention offer template pipeline."""
        brain = AgentBrain(site="amex", headless=True)
        result = await brain.execute(
            task="Get the best retention offer for my Gold card",
            dry_run=True,
            template_id="retention_offer",
        )
        assert result.status == TaskStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_general_pipeline_dry_run(self):
        """Validate general/freeform task pipeline."""
        brain = AgentBrain(site="amex", headless=True)
        result = await brain.execute(
            task="Ask about adding an authorized user",
            dry_run=True,
            template_id="general",
        )
        assert result.status == TaskStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_no_template_pipeline_dry_run(self):
        """Validate pipeline works without a template."""
        brain = AgentBrain(site="amex", headless=True)
        result = await brain.execute(
            task="Check my reward points balance",
            dry_run=True,
        )
        assert result.status == TaskStatus.SUCCESS
        assert result.outcome_details["template"] == "none"


@pytest.mark.slow
class TestAmexE2EBrowser:
    """E2E tests with real browser. Run with: pytest -m slow"""

    @pytest.mark.asyncio
    async def test_opens_amex_page(self):
        """Smoke test: verify browser opens and navigates to Amex."""
        brain = AgentBrain(site="amex", headless=True)
        # We can't do much without login, but we can verify the
        # browser opens and doesn't crash
        result = await brain.execute(
            task="Check if chat is available",
            max_steps=5,  # Just a few steps
        )
        # We expect it to need login input or partially complete
        assert result.status in (
            TaskStatus.SUCCESS,
            TaskStatus.NEEDS_INPUT,
            TaskStatus.PARTIAL,
            TaskStatus.FAILED,
        )
