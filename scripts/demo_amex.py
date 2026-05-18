#!/usr/bin/env python3
"""Demo script for Flying Pig AI — Amex fee negotiation.

Usage:
    # Dry run (no browser, validates pipeline)
    python scripts/demo_amex.py --dry-run

    # Full run (launches a controlled browser-use profile)
    python scripts/demo_amex.py

    # With template
    python scripts/demo_amex.py --template negotiate_fee

    # With specific model
    python scripts/demo_amex.py --model cliproxyapi
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.brain import AgentBrain, TaskStatus  # noqa: E402
from src.agent.navigator import ChatNavigator  # noqa: E402
from src.sites.amex import AmexAdapter  # noqa: E402


async def run_launch_smoke(headless: bool = False) -> int:
    """Launch Chrome with the user's profile and navigate to Amex without agent input."""
    navigator = ChatNavigator(site_adapter=AmexAdapter(), headless=headless)
    browser_session = await navigator.open_chat()
    page = await browser_session.get_current_page()
    current_url = await page.get_url()
    title = await page.get_title()
    print("✅ Controlled browser launched and navigation completed", flush=True)
    print(f"Current URL: {current_url}", flush=True)
    print(f"Title: {title}", flush=True)
    await browser_session.stop()
    return 0


async def run_demo(
    task: str,
    template: str | None = None,
    model: str | None = None,
    dry_run: bool = False,
    headless: bool = False,
    max_steps: int = 50,
):
    """Run the Amex demo."""
    print("🐷 Flying Pig AI — Amex Demo")
    print("=" * 60)
    print(f"Task: {task}")
    if template:
        print(f"Template: {template}")
    print(f"Model: {model or 'claude (default)'}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"Headless: {headless}")
    print("=" * 60)

    if not dry_run:
        print()
        print("⚠️  This legacy demo launches a clean controlled browser profile.")
        print("    For live supervised runs, prefer scripts/start.py.")
        print("    You may need to log in to Amex manually in the browser window.")
        print("    The agent will then navigate to chat and handle your request.")
        print()

    brain = AgentBrain(
        site="amex",
        headless=headless,
        input_mode="cli",
        model=model,
    )

    print("🚀 Starting agent...")
    result = await brain.execute(
        task=task,
        dry_run=dry_run,
        max_steps=max_steps,
        template_id=template,
    )

    print()
    print("=" * 60)
    print("📊 RESULTS")
    print("=" * 60)

    status_emoji = {
        TaskStatus.SUCCESS: "✅",
        TaskStatus.PARTIAL: "⚠️",
        TaskStatus.FAILED: "❌",
        TaskStatus.NEEDS_INPUT: "❓",
    }

    print(f"Status: {status_emoji.get(result.status, '?')} {result.status}")
    print(f"Summary: {result.summary}")
    print(f"Steps: {result.steps_taken}")
    print(f"Duration: {result.duration_seconds:.1f}s")

    if result.outcome_details:
        print("\nOutcome Details:")
        for k, v in result.outcome_details.items():
            if v:
                print(f"  {k}: {v}")

    if result.transcript_path:
        print(f"\n📄 Session saved: {result.transcript_path}")

    if result.transcript:
        print(f"\n📝 Transcript ({len(result.transcript)} steps):")
        for i, step in enumerate(result.transcript[:10], 1):
            display = step[:200] + "..." if len(step) > 200 else step
            print(f"  [{i}] {display}")
        if len(result.transcript) > 10:
            print(f"  ... and {len(result.transcript) - 10} more steps")

    return result


def main():
    parser = argparse.ArgumentParser(description="Flying Pig AI — Amex Demo")
    parser.add_argument(
        "--task",
        default=(
            "I'd like to negotiate my annual fee. "
            "I'm considering whether the card is worth keeping."
        ),
        help="Task for the agent",
    )
    parser.add_argument(
        "--template",
        default=None,
        choices=["negotiate_fee", "dispute_charge", "retention_offer", "general"],
        help="Use a pre-built task template",
    )
    parser.add_argument(
        "--model",
        default=None,
        choices=[
            "claude",
            "claude-sonnet",
            "claude-opus",
            "openai",
            "gpt-4o",
            "cliproxyapi",
            "cliproxy",
            "gpt-5.5",
            "gemini",
            "gemini-flash",
            "gemini-pro",
        ],
        help="LLM model to use",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate pipeline without opening browser",
    )
    parser.add_argument(
        "--launch-smoke",
        action="store_true",
        help="Launch Chrome and navigate to Amex without running the agent loop",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run browser in headless mode",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=50,
        help="Maximum agent steps",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    if args.launch_smoke:
        try:
            sys.exit(asyncio.run(run_launch_smoke(headless=args.headless)))
        except RuntimeError as e:
            print(f"❌ {e}", file=sys.stderr)
            sys.exit(1)

    result = asyncio.run(
        run_demo(
            task=args.task,
            template=args.template,
            model=args.model,
            dry_run=args.dry_run,
            headless=args.headless,
            max_steps=args.max_steps,
        )
    )

    sys.exit(0 if result.status in (TaskStatus.SUCCESS, TaskStatus.PARTIAL) else 1)


if __name__ == "__main__":
    main()
