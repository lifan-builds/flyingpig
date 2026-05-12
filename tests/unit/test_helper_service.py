from __future__ import annotations

from argparse import Namespace

from src import helper_service


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
        "--no-browser",
        "--host",
        "127.0.0.1",
        "--port",
        "8765",
        "--cdp-port",
        "9222",
    ]
    assert payload["StandardOutPath"].endswith(".flyingpig/logs/helper.out.log")
