"""Beta helper process for the Flying Pig side-panel runtime."""

from __future__ import annotations

import argparse
import logging
import sys

import uvicorn

from src.agent.browser_runtime import ChromeLaunchConfig, launch_cdp_chrome
from src.daemon.server import create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Flying Pig local helper for beta side-panel sessions.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Helper host")
    parser.add_argument("--port", type=int, default=8765, help="Helper WebSocket/API port")
    parser.add_argument("--cdp-port", type=int, default=9222, help="Chrome debugging port")
    parser.add_argument(
        "--chrome-profile",
        choices=["default", "dedicated"],
        default="default",
        help=(
            "Chrome profile mode. 'default' uses FlyingPig's persistent copy of "
            "the user's default profile; 'dedicated' starts clean."
        ),
    )
    parser.add_argument(
        "--chrome-user-data-dir",
        default=None,
        help="Advanced: explicit Chrome user-data directory",
    )
    parser.add_argument(
        "--initial-url",
        default="https://www.americanexpress.com/us/customer-service/",
        help="Page to open in the FlyingPig Chrome window",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Start only the helper daemon; do not launch Chrome",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    cdp_url = f"http://127.0.0.1:{args.cdp_port}"
    if not args.no_browser:
        try:
            cdp_url = launch_cdp_chrome(
                ChromeLaunchConfig(
                    cdp_port=args.cdp_port,
                    chrome_profile=args.chrome_profile,
                    chrome_user_data_dir=args.chrome_user_data_dir,
                    initial_url=args.initial_url,
                )
            )
        except Exception as exc:
            print(f"Flying Pig helper could not launch Chrome: {type(exc).__name__}: {exc}")
            sys.exit(1)

    print(f"Flying Pig helper online: ws://{args.host}:{args.port}/ws")
    print(f"Browser endpoint for the side panel: {cdp_url}")
    print("Keep this helper running while the Chrome side panel controls the agent.")

    uvicorn.run(
        create_app(),
        host=args.host,
        port=args.port,
        log_level="debug" if args.verbose else "info",
    )


if __name__ == "__main__":
    main()
