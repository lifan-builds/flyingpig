"""CLI entry point for Flying Pig AI."""

import argparse
import asyncio
import logging
import sys

from src.agent.brain import AgentBrain, TaskStatus
from src.sites.task_templates import get_templates, list_all_templates


def _print_templates():
    """Print all available task templates."""
    all_templates = list_all_templates()
    print("\n🐷 Available Task Templates")
    print("=" * 60)
    for site, templates in all_templates.items():
        print(f"\n  Site: {site}")
        print(f"  {'─' * 50}")
        for t in templates:
            print(f"    {t.id:<20} {t.name}")
            print(f"    {'':20} {t.description}")
            if t.example_usage:
                print(f"    {'':20} Example: {t.example_usage}")
            print()


def _print_result(result):
    """Print task result in a formatted way."""
    status_emoji = {
        TaskStatus.SUCCESS: "✅",
        TaskStatus.PARTIAL: "⚠️",
        TaskStatus.FAILED: "❌",
        TaskStatus.NEEDS_INPUT: "❓",
    }

    print(f"\n{'='*60}")
    print(f"{status_emoji.get(result.status, '❓')} Status: {result.status}")
    print(f"{'='*60}")
    print(f"Summary: {result.summary}")
    print(f"Steps: {result.steps_taken} | Duration: {result.duration_seconds:.1f}s")

    if result.outcome_details:
        if result.outcome_details.get("confirmation_number"):
            print(f"Confirmation #: {result.outcome_details['confirmation_number']}")
        if result.outcome_details.get("amount_saved"):
            print(f"💰 Amount saved: {result.outcome_details['amount_saved']}")
        if result.outcome_details.get("next_steps"):
            print(f"Next steps: {result.outcome_details['next_steps']}")

    if result.transcript_path:
        print(f"\n📄 Full session saved to: {result.transcript_path}")


def main():
    parser = argparse.ArgumentParser(
        prog="flyingpig",
        description="Flying Pig AI (客服上树) — AI customer service agent",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- Run command ---
    run_parser = subparsers.add_parser("run", help="Run a customer service task")
    run_parser.add_argument(
        "task", help="e.g. 'negotiate my annual fee' or 'cancel my subscription'"
    )
    run_parser.add_argument("--site", required=True, help="Target site: amex, ...")
    run_parser.add_argument(
        "--template", default=None, help="Use a pre-built task template (e.g. negotiate_fee)"
    )
    run_parser.add_argument(
        "--headless", action="store_true", default=False, help="Run browser headless"
    )
    run_parser.add_argument(
        "--dry-run", action="store_true", default=False, help="Plan without executing"
    )
    run_parser.add_argument(
        "--max-steps", type=int, default=100, help="Max agent steps (default: 100)"
    )
    run_parser.add_argument(
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
        ],
        help="LLM model to use (default: claude-sonnet)",
    )
    run_parser.add_argument(
        "--verbose", "-v", action="store_true", default=False, help="Verbose logging"
    )

    # --- Templates command ---
    subparsers.add_parser("templates", help="List available task templates")

    # --- Legacy support: if no subcommand, treat positional arg as task ---
    # This handles: flyingpig "negotiate my fee" --site amex
    parser.add_argument("legacy_task", nargs="?", help=argparse.SUPPRESS)
    parser.add_argument("--site", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--template", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--headless", action="store_true", default=False, help=argparse.SUPPRESS)
    parser.add_argument("--dry-run", action="store_true", default=False, help=argparse.SUPPRESS)
    parser.add_argument("--max-steps", type=int, default=100, help=argparse.SUPPRESS)
    parser.add_argument("--model", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--verbose", "-v", action="store_true", default=False,
                        help=argparse.SUPPRESS)

    args = parser.parse_args()

    # Handle subcommands
    if args.command == "templates":
        _print_templates()
        sys.exit(0)

    # Handle run command or legacy mode
    task = args.task if args.command == "run" else args.legacy_task
    site = args.site

    if not task:
        parser.print_help()
        print("\n💡 Quick start:")
        print("  flyingpig run 'negotiate my annual fee' --site amex")
        print("  flyingpig run 'dispute a $50 charge from Amazon' --site amex")
        print("  flyingpig templates")
        sys.exit(1)

    if not site:
        print("❌ Error: --site is required. Try: --site amex")
        sys.exit(1)

    # If a template is specified, show what template we're using
    if args.template:
        templates = get_templates(site)
        template_names = [t.id for t in templates]
        if args.template not in template_names:
            print(f"❌ Unknown template '{args.template}'. Available: {', '.join(template_names)}")
            sys.exit(1)
        template = next(t for t in templates if t.id == args.template)
        print(f"📋 Using template: {template.name} — {template.description}")

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    print(f"\n🐷 Flying Pig AI — starting task on {site}")
    if args.dry_run:
        print("   (DRY RUN — no browser will be opened)")
    print()

    brain = AgentBrain(
        site=site,
        headless=args.headless,
        input_mode="cli",
        model=args.model,
    )
    result = asyncio.run(
        brain.execute(
            task=task,
            dry_run=args.dry_run,
            max_steps=args.max_steps,
            template_id=args.template,
        )
    )

    _print_result(result)

    if result.status == TaskStatus.NEEDS_INPUT:
        print("\n❓ The agent needs your input to continue.")
        print("Please provide the requested information and re-run.")
        sys.exit(2)

    sys.exit(0 if result.status == TaskStatus.SUCCESS else 1)


if __name__ == "__main__":
    main()
