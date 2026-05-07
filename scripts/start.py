#!/usr/bin/env python3
"""One-command launcher for Flying Pig AI.

Usage:
    python scripts/start.py
    python scripts/start.py --browser-only
    python scripts/start.py --template dispute_charge
    python scripts/start.py --task "Cancel my Gold card subscription"
    python scripts/start.py --model cliproxyapi
    python scripts/start.py --attach
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.brain import AgentBrain, TaskStatus  # noqa: E402
from src.agent.browser_runtime import ChromeLaunchConfig, launch_cdp_chrome  # noqa: E402


async def run(args: argparse.Namespace) -> int:
    cdp_url = args.cdp_url or args.attach
    should_launch_flyingpig_chrome = (
        not args.dry_run and (args.browser_only or args.launch_flyingpig_chrome or not cdp_url)
    )
    if should_launch_flyingpig_chrome:
        cdp_url = launch_cdp_chrome(
            ChromeLaunchConfig(
                cdp_port=args.cdp_port,
                chrome_profile=args.chrome_profile,
                chrome_user_data_dir=args.chrome_user_data_dir,
                initial_url=args.initial_url,
                dashboard_url=args.dashboard_url,
            )
        )
        if args.browser_only:
            print(f"   Chrome is ready for the side panel at {cdp_url}.")
            return 0
        input(
            "   Log in / prepare the visible Chrome tab, then press Enter here "
            "to let Flying Pig attach: "
        )
    elif args.browser_only:
        print(f"   Chrome is ready for the side panel at {cdp_url}.")
        return 0

    brain = AgentBrain(
        site=args.site,
        headless=False,
        input_mode="cli",
        model=args.model,
        fallback_model=args.fallback_model,
        cdp_url=cdp_url,
        navigate_on_attach=args.navigate_on_attach,
    )

    print(f"🐷 Running task: {args.task}")
    if args.dry_run:
        print("   Dry run only; no Chrome session will be opened.")
    elif cdp_url:
        print(f"   Flying Pig will attach to Chrome at {cdp_url}.")
        print("   Keep the intended Amex tab active in that Chrome window.")
    else:
        print("   Flying Pig will launch a dedicated visible Chrome window.")
    result = await brain.execute(
        task=args.task,
        dry_run=args.dry_run,
        max_steps=args.max_steps,
        template_id=args.template,
    )

    print()
    emoji = {
        TaskStatus.SUCCESS: "✅",
        TaskStatus.PARTIAL: "⚠️",
        TaskStatus.FAILED: "❌",
        TaskStatus.NEEDS_INPUT: "❓",
    }.get(result.status, "?")
    print(f"{emoji} {result.status}: {result.summary}")
    print(f"   {result.steps_taken} steps in {result.duration_seconds:.1f}s")
    if result.transcript_path:
        print(f"   Session: {result.transcript_path}")
    return 0 if result.status in (TaskStatus.SUCCESS, TaskStatus.PARTIAL) else 1


def main() -> None:
    p = argparse.ArgumentParser(
        description="Flying Pig AI — supervised customer-service launcher",
        epilog=(
            "Typical use: run this with no flags, prepare the visible Chrome tab when "
            "prompted, then let Flying Pig work. Advanced CDP/profile flags still "
            "exist for debugging and scripted runs."
        ),
    )
    p.add_argument("--site", default="amex", help=argparse.SUPPRESS)
    p.add_argument(
        "--task",
        default=(
            "I'd like to negotiate my annual fee. "
            "I'm considering whether the card is worth keeping."
        ),
    )
    p.add_argument(
        "--template",
        default="negotiate_fee",
        choices=["negotiate_fee", "dispute_charge", "retention_offer", "general"],
        help="Task playbook to use",
    )
    p.add_argument(
        "--model",
        default=None,
        choices=[
            "claude", "claude-sonnet", "claude-opus",
            "openai", "gpt-4o",
            "cliproxyapi", "cliproxy", "gpt-5.5",
            "gemini", "gemini-flash", "gemini-pro",
        ],
    )
    p.add_argument(
        "--fallback-model",
        default=None,
        choices=[
            "claude", "claude-sonnet", "claude-opus",
            "openai", "gpt-4o",
            "cliproxyapi", "cliproxy", "gpt-5.5",
            "gemini", "gemini-flash", "gemini-pro",
        ],
        help="Fallback model to try if the primary LLM fails mid-run.",
    )
    p.add_argument("--max-steps", type=int, default=50, help=argparse.SUPPRESS)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the task prompt without opening or attaching to Chrome.",
    )
    p.add_argument(
        "--browser-only",
        action="store_true",
        help="Launch copied-profile Chrome with CDP, then exit for side-panel use.",
    )
    p.add_argument(
        "--attach",
        nargs="?",
        const="http://127.0.0.1:9222",
        default=None,
        metavar="CDP_URL",
        help=(
            "Attach to an already prepared remote-debugging Chrome tab "
            "(default: http://127.0.0.1:9222)."
        ),
    )
    p.add_argument(
        "--cdp-url",
        default=None,
        help=argparse.SUPPRESS,
    )
    p.add_argument(
        "--launch-flyingpig-chrome",
        "--launch-cdp-chrome",
        dest="launch_flyingpig_chrome",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    p.add_argument("--cdp-port", type=int, default=9222, help=argparse.SUPPRESS)
    p.add_argument(
        "--chrome-profile",
        choices=["dedicated", "default", "existing"],
        default="default",
        help=argparse.SUPPRESS,
    )
    p.add_argument(
        "--chrome-user-data-dir",
        default=None,
        help=argparse.SUPPRESS,
    )
    p.add_argument(
        "--initial-url",
        default="https://www.americanexpress.com/us/customer-service/",
        help=argparse.SUPPRESS,
    )
    p.add_argument(
        "--dashboard-url",
        default=None,
        help=argparse.SUPPRESS,
    )
    p.add_argument(
        "--navigate-on-attach",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    sys.exit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
