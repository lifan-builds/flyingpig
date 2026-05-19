"""Beta helper process for the Flying Pig dashboard runtime."""

from __future__ import annotations

import argparse
import logging
import sys
import threading
import webbrowser

import uvicorn

from src.daemon.server import create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Flying Pig local helper for beta dashboard sessions.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Helper host")
    parser.add_argument("--port", type=int, default=8765, help="Helper WebSocket/API port")
    parser.add_argument("--cdp-port", type=int, default=9222, help="Chrome debugging port")
    parser.add_argument(
        "--chrome-profile",
        choices=["default", "dedicated"],
        default="dedicated",
        help=(
            "Chrome profile mode. 'dedicated' uses FlyingPig's isolated work profile; "
            "'default' uses FlyingPig's persistent copy of the user's default profile."
        ),
    )
    parser.add_argument(
        "--chrome-user-data-dir",
        default=None,
        help="Advanced: explicit Chrome user-data directory",
    )
    parser.add_argument(
        "--initial-url",
        default="about:blank",
        help="Page to open in the Flying Pig work window",
    )
    parser.add_argument(
        "--launch-browser",
        action="store_true",
        help=(
            "Launch the Flying Pig work window immediately. By default the dashboard "
            "opens first and the work window launches when the user clicks Launch Work Window."
        ),
    )
    parser.add_argument(
        "--no-dashboard",
        action="store_true",
        help="Do not open the localhost dashboard in the user's browser",
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
    if args.launch_browser:
        from src.agent.browser_runtime import ChromeLaunchConfig, launch_cdp_chrome

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
    dashboard_url = f"http://{args.host}:{args.port}/dashboard/"
    print(f"Dashboard: {dashboard_url}")
    print(f"Browser endpoint for the dashboard: {cdp_url}")
    print("Press Ctrl+C in this terminal to stop the helper when you are done.")

    if not args.no_dashboard:
        threading.Timer(0.8, webbrowser.open, args=(dashboard_url,)).start()

    uvicorn.run(
        create_app(),
        host=args.host,
        port=args.port,
        log_level="debug" if args.verbose else "info",
    )


if __name__ == "__main__":
    main()
