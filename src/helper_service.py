"""Install and manage the Flying Pig beta helper as a macOS LaunchAgent."""

from __future__ import annotations

import argparse
import os
import plistlib
import subprocess
import sys
from pathlib import Path

LABEL = "com.flyingpig.helper"
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
PLIST_PATH = LAUNCH_AGENTS_DIR / f"{LABEL}.plist"
LOG_DIR = Path.home() / ".flyingpig" / "logs"
ROOT = Path(__file__).resolve().parent.parent


def service_target() -> str:
    return f"gui/{os.getuid()}/{LABEL}"


def plist_payload(args: argparse.Namespace) -> dict:
    program_arguments = [
        sys.executable,
        "-m",
        "src.helper",
        "--no-dashboard",
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--cdp-port",
        str(args.cdp_port),
    ]
    if args.verbose:
        program_arguments.append("--verbose")

    return {
        "Label": LABEL,
        "ProgramArguments": program_arguments,
        "WorkingDirectory": str(ROOT),
        "RunAtLoad": True,
        "KeepAlive": {
            "SuccessfulExit": False,
        },
        "StandardOutPath": str(LOG_DIR / "helper.out.log"),
        "StandardErrorPath": str(LOG_DIR / "helper.err.log"),
        "EnvironmentVariables": {
            "PYTHONUNBUFFERED": "1",
        },
    }


def run_launchctl(*parts: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["launchctl", *parts],
        capture_output=True,
        text=True,
        check=check,
    )


def launchctl_failure_message(action: str, exc: subprocess.CalledProcessError) -> str:
    details = (exc.stderr or exc.stdout or "").strip()
    command = " ".join(exc.cmd) if isinstance(exc.cmd, list) else str(exc.cmd)
    message = [
        f"Could not {action} Flying Pig helper.",
        f"`{command}` exited with status {exc.returncode}.",
    ]
    if details:
        message.append(details)
    message.append(
        "Try `flyingpig-macos-helper status`, then reinstall with "
        "`flyingpig-macos-helper install` if the LaunchAgent is missing or stale."
    )
    return "\n".join(message)


def run_launchctl_or_exit(action: str, *parts: str) -> subprocess.CompletedProcess[str]:
    try:
        return run_launchctl(*parts)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(launchctl_failure_message(action, exc)) from exc


def install(args: argparse.Namespace) -> None:
    LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with PLIST_PATH.open("wb") as f:
        plistlib.dump(plist_payload(args), f, sort_keys=False)

    run_launchctl("bootout", f"gui/{os.getuid()}", str(PLIST_PATH), check=False)
    run_launchctl_or_exit("install", "bootstrap", f"gui/{os.getuid()}", str(PLIST_PATH))
    run_launchctl_or_exit("enable", "enable", service_target())
    print(f"Installed Flying Pig helper LaunchAgent: {PLIST_PATH}")
    print(
        "The helper will start at login. Open "
        f"http://{args.host}:{args.port}/dashboard/ and use Open Work Window."
    )


def uninstall(_args: argparse.Namespace) -> None:
    run_launchctl("bootout", f"gui/{os.getuid()}", str(PLIST_PATH), check=False)
    if PLIST_PATH.exists():
        PLIST_PATH.unlink()
    print("Uninstalled Flying Pig helper LaunchAgent.")


def start(_args: argparse.Namespace) -> None:
    if not PLIST_PATH.exists():
        raise SystemExit("LaunchAgent is not installed. Run: flyingpig-macos-helper install")
    run_launchctl("bootstrap", f"gui/{os.getuid()}", str(PLIST_PATH), check=False)
    run_launchctl_or_exit("start", "kickstart", "-k", service_target())
    print("Started Flying Pig helper.")


def stop(_args: argparse.Namespace) -> None:
    result = run_launchctl("bootout", service_target(), check=False)
    if result.returncode == 0:
        print("Stopped Flying Pig helper.")
        return

    status_result = run_launchctl("print", service_target(), check=False)
    if status_result.returncode != 0:
        print("Flying Pig helper is not running.")
        return

    raise SystemExit(
        "\n".join(
            [
                "Could not stop Flying Pig helper.",
                "`launchctl bootout "
                f"{service_target()}` exited with status {result.returncode}.",
                (result.stderr or result.stdout or "").strip(),
                "Try `flyingpig-macos-helper status`, then reinstall with "
                "`flyingpig-macos-helper install` if the LaunchAgent is missing or stale.",
            ]
        )
    )


def status(_args: argparse.Namespace) -> None:
    result = run_launchctl("print", service_target(), check=False)
    if result.returncode == 0:
        print(result.stdout)
        return
    print("Flying Pig helper is not running.")
    if PLIST_PATH.exists():
        print(f"LaunchAgent is installed at {PLIST_PATH}.")
    else:
        print("LaunchAgent is not installed.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install", help="Install and start the helper")
    install_parser.add_argument("--host", default="127.0.0.1")
    install_parser.add_argument("--port", type=int, default=8765)
    install_parser.add_argument("--cdp-port", type=int, default=9222)
    install_parser.add_argument("--verbose", "-v", action="store_true")
    install_parser.set_defaults(func=install)

    subparsers.add_parser("uninstall", help="Stop and remove the helper").set_defaults(
        func=uninstall
    )
    subparsers.add_parser("start", help="Start the installed helper").set_defaults(func=start)
    subparsers.add_parser("stop", help="Stop the installed helper").set_defaults(func=stop)
    subparsers.add_parser("status", help="Show helper status").set_defaults(func=status)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
