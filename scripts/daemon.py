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

from src.daemon.server import create_app  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Flying Pig WebSocket daemon")
    p.add_argument("--port", type=int, default=8765, help="WebSocket server port")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    app = create_app()
    print(f"🐷 Daemon listening on ws://{args.host}:{args.port}/ws")
    print("   Browser sessions attach to CDP or launch FlyingPig-controlled Chrome.")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
