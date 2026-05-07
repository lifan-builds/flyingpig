#!/usr/bin/env python3
"""Run Flying Pig against the local mock Amex chat site."""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.brain import AgentBrain  # noqa: E402
from src.sites.amex import AmexAdapter  # noqa: E402


async def _answer_mock_prompts(brain: AgentBrain, task: asyncio.Task) -> None:
    last_question: str | None = None
    for _ in range(360):
        question = brain.input_handler.pending_question
        if question and question != last_question:
            last_question = question
            brain.input_handler.provide_input(
                "Yes, confirmed. Refer to the Amex Platinum account generically. "
                "Continue with the test task, and you can accept a $50 statement "
                "credit if offered."
            )
        if task.done():
            return
        await asyncio.sleep(0.5)


async def run(args: argparse.Namespace) -> int:
    AmexAdapter.chat_url = args.url

    brain = AgentBrain(
        site="amex",
        headless=args.headless,
        input_mode="api",
        model=args.model,
        browser_mode=args.browser_mode,
        use_vision=not args.no_vision,
        llm_timeout=args.llm_timeout,
    )
    task = (
        "Open chat and ask them to cancel my account. If they offer a credit, "
        "accept it and finish after obtaining the confirmation number."
    )

    run_task = asyncio.create_task(
        brain.execute(
            task=task,
            max_steps=args.max_steps,
            save_dir=args.save_dir,
        )
    )
    await _answer_mock_prompts(brain, run_task)
    result = await run_task

    print(f"STATUS {result.status}")
    print(f"SUMMARY {result.summary}")
    print(f"PATH {result.transcript_path}")
    print(f"STEPS {result.steps_taken}")
    print("CHAT_TRANSCRIPT_START")
    print("\n".join(result.chat_transcript))
    print("TRANSCRIPT_START")
    print("\n---\n".join(result.transcript))
    return 0 if result.status.value in {"success", "partial"} else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8086/?logged_in=true",
        help="Mock Amex chat URL.",
    )
    parser.add_argument("--model", default="cliproxyapi")
    parser.add_argument(
        "--browser-mode",
        default="controlled",
        choices=["controlled", "fresh"],
    )
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--no-vision", action="store_true")
    parser.add_argument("--llm-timeout", type=int, default=180)
    parser.add_argument("--max-steps", type=int, default=18)
    parser.add_argument("--save-dir", default="recordings/mock_run")
    raise SystemExit(asyncio.run(run(parser.parse_args())))


if __name__ == "__main__":
    main()
