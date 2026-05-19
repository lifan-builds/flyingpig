from __future__ import annotations

import subprocess
from argparse import Namespace

from src import helper, helper_service


def test_launch_agent_plist_runs_background_helper():
    payload = helper_service.plist_payload(
        Namespace(host="127.0.0.1", port=8765, cdp_port=9222, verbose=False)
    )

    assert payload["Label"] == "com.flyingpig.helper"
    assert payload["RunAtLoad"] is True
    assert payload["KeepAlive"] == {"SuccessfulExit": False}
    assert payload["ProgramArguments"][1:] == [
        "-m",
        "src.helper",
        "--no-dashboard",
        "--host",
        "127.0.0.1",
        "--port",
        "8765",
        "--cdp-port",
        "9222",
    ]
    assert payload["StandardOutPath"].endswith(".flyingpig/logs/helper.out.log")


def test_helper_cli_opens_dashboard_without_launching_work_window_by_default():
    args = helper.build_parser().parse_args([])

    assert args.launch_browser is False
    assert args.no_dashboard is False


def test_launchctl_failure_message_includes_action_status_and_recovery():
    exc = subprocess.CalledProcessError(
        returncode=113,
        cmd=["launchctl", "kickstart", "-k", "gui/501/com.flyingpig.helper"],
        stderr='Could not find service "com.flyingpig.helper"',
    )

    message = helper_service.launchctl_failure_message("start", exc)

    assert "Could not start Flying Pig helper." in message
    assert "exited with status 113" in message
    assert 'Could not find service "com.flyingpig.helper"' in message
    assert "flyingpig-macos-helper status" in message
