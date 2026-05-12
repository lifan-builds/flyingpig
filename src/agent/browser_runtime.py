"""Browser runtime policy for Flying Pig live and test runs."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

CHROME_APP = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEFAULT_CHROME_USER_DATA_DIR = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
DEDICATED_CHROME_USER_DATA_DIR = Path.home() / ".flyingpig" / "chrome-cdp-profile"
DEFAULT_COPY_CHROME_USER_DATA_DIR = Path.home() / ".flyingpig" / "chrome-cdp-default-copy"


@dataclass(frozen=True)
class ChromeLaunchConfig:
    """Configuration for a visible CDP Chrome run."""

    cdp_port: int = 9222
    chrome_profile: str = "default"
    chrome_user_data_dir: str | None = None
    initial_url: str = "https://www.americanexpress.com/us/customer-service/"
    dashboard_url: str | None = None


def regular_chrome_is_running() -> bool:
    """Return True when the user's normal Chrome app is already open."""
    try:
        result = subprocess.run(
            ["ps", "ax", "-o", "command="],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    if result.returncode != 0:
        return False

    for line in result.stdout.splitlines():
        if "/Google Chrome.app/Contents/MacOS/Google Chrome" not in line:
            continue
        if "browser-use-user-data-dir-" in line:
            continue
        return True
    return False


def chrome_user_data_dir(profile: str, custom_dir: str | None) -> Path:
    if custom_dir:
        return Path(custom_dir).expanduser()
    if profile == "existing":
        return DEFAULT_CHROME_USER_DATA_DIR
    if profile == "default":
        return DEFAULT_COPY_CHROME_USER_DATA_DIR
    return DEDICATED_CHROME_USER_DATA_DIR


def debugger_is_ready(port: int) -> bool:
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/json/version",
            timeout=1,
        ) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def wait_for_debugger(port: int, timeout_seconds: int = 20) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if debugger_is_ready(port):
            return
        time.sleep(0.25)
    raise RuntimeError(f"Chrome remote debugging did not start on port {port}")


def launch_cdp_chrome(config: ChromeLaunchConfig) -> str:
    """Launch a visible FlyingPig-owned Chrome that can be attached over CDP.

    The `existing` profile mode launches the literal user Chrome profile, so
    normal Chrome must already be closed. The dedicated and copied-profile modes
    use separate user-data directories.
    """
    cdp_url = f"http://127.0.0.1:{config.cdp_port}"
    if debugger_is_ready(config.cdp_port):
        print(f"   Reusing Chrome remote debugging endpoint at {cdp_url}")
        return cdp_url

    user_data_dir = chrome_user_data_dir(
        config.chrome_profile,
        config.chrome_user_data_dir,
    )
    if config.chrome_profile == "existing" and config.chrome_user_data_dir is None:
        raise RuntimeError(
            "Chrome blocks remote debugging on the literal default user profile. "
            "Use --chrome-profile default for FlyingPig's persistent copied profile, "
            "or pass --chrome-user-data-dir with a non-default Chrome profile."
        )
    if config.chrome_profile == "default" and config.chrome_user_data_dir is None:
        ensure_default_profile_copy(user_data_dir)
    user_data_dir.mkdir(parents=True, exist_ok=True)

    command = [
        CHROME_APP,
        f"--remote-debugging-port={config.cdp_port}",
        f"--user-data-dir={user_data_dir}",
        "--profile-directory=Default",
        "--new-window",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1280,900",
        "--window-position=80,80",
        config.initial_url,
    ]

    print("   Launching visible FlyingPig Chrome with remote debugging.")
    print(f"   Profile dir: {user_data_dir}")
    subprocess.Popen(command, start_new_session=True)
    wait_for_debugger(config.cdp_port)
    if config.dashboard_url:
        open_dashboard_tab(
            port=config.cdp_port,
            dashboard_url=config.dashboard_url,
            target_url=config.initial_url,
        )
    return cdp_url


def open_dashboard_tab(
    *,
    port: int,
    dashboard_url: str,
    target_url: str,
) -> None:
    """Open dashboard status beside the task tab, then reactivate task tab."""
    try:
        task_target_id = find_debugger_target_id(port=port, url_prefix=target_url)
        encoded_dashboard_url = urllib.parse.quote(dashboard_url, safe="")
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/json/new?{encoded_dashboard_url}",
            method="PUT",
        )
        urllib.request.urlopen(request, timeout=2).close()
        if task_target_id:
            urllib.request.urlopen(
                f"http://127.0.0.1:{port}/json/activate/{task_target_id}",
                timeout=2,
            ).close()
        print(f"   Dashboard tab: {dashboard_url}")
    except (OSError, urllib.error.URLError) as exc:
        print(f"   Dashboard tab could not be opened automatically: {exc}")


def find_debugger_target_id(*, port: int, url_prefix: str) -> str | None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=2) as response:
            targets = json.load(response)
    except (OSError, urllib.error.URLError, ValueError):
        return None

    for target in targets:
        if target.get("type") != "page":
            continue
        if str(target.get("url", "")).startswith(url_prefix):
            return target.get("id")
    return None


def ensure_default_profile_copy(destination: Path) -> None:
    if destination.exists():
        return
    if not DEFAULT_CHROME_USER_DATA_DIR.exists():
        raise RuntimeError(f"Chrome profile not found: {DEFAULT_CHROME_USER_DATA_DIR}")
    if regular_chrome_is_running():
        raise RuntimeError(
            "The default-profile copy does not exist yet. Quit normal Chrome once "
            "to create it safely, or use --chrome-profile dedicated to launch a "
            "FlyingPig Chrome alongside your current Chrome."
        )
    print("   Creating CDP-compatible copy of your default Chrome profile.")
    shutil.copytree(
        DEFAULT_CHROME_USER_DATA_DIR,
        destination,
        ignore=_ignore_chrome_copy_noise,
        dirs_exist_ok=True,
    )


def _ignore_chrome_copy_noise(directory: str, names: list[str]) -> set[str]:
    ignored = {
        "SingletonCookie",
        "SingletonLock",
        "SingletonSocket",
        "BrowserMetrics",
        "Crashpad",
        "GrShaderCache",
        "GraphiteDawnCache",
        "Safe Browsing",
        "ShaderCache",
    }
    return {name for name in names if name in ignored}
