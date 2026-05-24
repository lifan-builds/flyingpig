#!/usr/bin/env python3
"""Flying Pig daemon — WebSocket API for running agent sessions.

Usage:
    python scripts/daemon.py
    python scripts/daemon.py --port 8765
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import uvicorn

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.browser_runtime import (  # noqa: E402
    ChromeLaunchConfig,
    launch_cdp_chrome,
    supported_chrome_profile_modes,
)
from src.daemon.server import create_app  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Flying Pig WebSocket daemon")
    p.add_argument("--port", type=int, default=8765, help="WebSocket server port")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--cdp-port", type=int, default=9222, help="Chrome debugging port")
    p.add_argument(
        "--chrome-profile",
        choices=sorted(supported_chrome_profile_modes()),
        default="dedicated",
        help=(
            "Chrome profile mode. 'dedicated' uses FlyingPig's isolated work profile; "
            "'default' uses FlyingPig's persistent copy of the user's default profile; "
            "'existing' uses an explicit user profile directory when provided."
        ),
    )
    p.add_argument(
        "--chrome-user-data-dir",
        default=None,
        help="Advanced: explicit Chrome user-data directory",
    )
    p.add_argument(
        "--initial-url",
        default="about:blank",
        help="Page to open in the controlled Chrome window",
    )
    p.add_argument(
        "--no-browser",
        action="store_true",
        help="Start only the helper daemon; do not launch controlled Chrome",
    )
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args()

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
            print(f"🐷 Could not launch controlled Chrome: {type(exc).__name__}: {exc}")
            print(
                "   Continuing with helper only. Use the dashboard's "
                "Open Work Window button."
            )

    app = create_app()
    print(f"🐷 Daemon listening on ws://{args.host}:{args.port}/ws")
    print(f"   Browser endpoint for the dashboard: {cdp_url}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
