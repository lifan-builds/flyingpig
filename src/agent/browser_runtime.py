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
from enum import StrEnum
from pathlib import Path

CHROME_APP = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEFAULT_CHROME_USER_DATA_DIR = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
DEDICATED_CHROME_USER_DATA_DIR = Path.home() / ".flyingpig" / "chrome-cdp-profile"
DEFAULT_COPY_CHROME_USER_DATA_DIR = Path.home() / ".flyingpig" / "chrome-cdp-default-copy"
DEFAULT_CDP_URL = "http://127.0.0.1:9222"


class ChromeProfileMode(StrEnum):
    """Supported profile modes for the Controlled Chrome Window."""

    DEDICATED = "dedicated"
    DEFAULT_COPY = "default"
    USER_DEFAULT = "existing"


@dataclass(frozen=True)
class ChromeLaunchConfig:
    """Configuration for a visible CDP Chrome run."""

    cdp_port: int = 9222
    chrome_profile: str = "dedicated"
    chrome_user_data_dir: str | None = None
    initial_url: str = "about:blank"
    dashboard_url: str | None = None
    disable_extensions: bool = True
    window_width: int = 1120
    window_height: int = 900
    window_left: int = 560
    window_top: int = 80


def supported_chrome_profile_modes() -> set[str]:
    """Return profile mode values accepted by the Controlled Chrome Window."""
    return {mode.value for mode in ChromeProfileMode}


def chrome_profile_label(profile: str) -> str:
    """Return a user-facing label for a Controlled Chrome profile mode."""
    labels = {
        ChromeProfileMode.DEDICATED.value: "Dedicated Flying Pig profile",
        ChromeProfileMode.DEFAULT_COPY.value: "Copied Chrome Default profile",
        ChromeProfileMode.USER_DEFAULT.value: "User default profile",
    }
    return labels.get(profile, profile)


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
    if profile == ChromeProfileMode.USER_DEFAULT.value:
        return DEFAULT_CHROME_USER_DATA_DIR
    if profile == ChromeProfileMode.DEFAULT_COPY.value:
        return DEFAULT_COPY_CHROME_USER_DATA_DIR
    return DEDICATED_CHROME_USER_DATA_DIR


def cdp_url_for_port(port: int) -> str:
    """Return the legacy localhost CDP URL for a port-only call site."""
    return f"http://127.0.0.1:{port}"


def normalize_cdp_url(cdp_url: str | None, default_port: int = 9222) -> str:
    """Normalize a CDP endpoint while preserving its explicit host.

    Users may enter endpoints as `localhost:9222`, `http://[::1]:9222`, or a
    full URL with a trailing path. The dashboard and helper should preserve the
    host because Chrome can bind IPv4 and IPv6 loopback differently.
    """
    raw = (cdp_url or DEFAULT_CDP_URL).strip()
    if not raw:
        raw = DEFAULT_CDP_URL
    if "://" not in raw:
        raw = f"http://{raw}"

    parsed = urllib.parse.urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"Invalid Chrome debugging endpoint: {cdp_url}")

    host = parsed.hostname
    port = parsed.port or default_port
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    return f"{parsed.scheme}://{host}:{port}"


def _cdp_base_url(*, port: int | None = None, cdp_url: str | None = None) -> str:
    if cdp_url is not None:
        return normalize_cdp_url(cdp_url)
    return cdp_url_for_port(port or 9222)


def debugger_is_ready(port: int | None = None, *, cdp_url: str | None = None) -> bool:
    base_url = _cdp_base_url(port=port, cdp_url=cdp_url)
    try:
        with urllib.request.urlopen(
            f"{base_url}/json/version",
            timeout=1,
        ) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError, ValueError):
        return False


def debugger_page_info(port: int | None = None, *, cdp_url: str | None = None) -> dict | None:
    """Return the first debuggable work-window page, if Chrome exposes one."""
    targets = debugger_targets(port, cdp_url=cdp_url)
    if targets is None:
        return None

    for target in targets:
        if target.get("type") != "page":
            continue
        return {
            "id": target.get("id"),
            "title": target.get("title") or "",
            "url": target.get("url") or "",
        }
    return None


def debugger_targets(port: int | None = None, *, cdp_url: str | None = None) -> list[dict] | None:
    """Return raw CDP targets for a running debug endpoint."""
    base_url = _cdp_base_url(port=port, cdp_url=cdp_url)
    try:
        with urllib.request.urlopen(f"{base_url}/json", timeout=2) as response:
            return json.load(response)
    except (OSError, urllib.error.URLError, ValueError):
        return None


def wait_for_debugger(
    port: int | None = None,
    timeout_seconds: int = 20,
    *,
    cdp_url: str | None = None,
) -> None:
    base_url = _cdp_base_url(port=port, cdp_url=cdp_url)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if debugger_is_ready(cdp_url=base_url):
            return
        time.sleep(0.25)
    raise RuntimeError(f"Chrome remote debugging did not start at {base_url}")


def launch_cdp_chrome(config: ChromeLaunchConfig) -> str:
    """Launch a visible FlyingPig-owned Chrome that can be attached over CDP.

    The `existing` profile mode launches the literal user Chrome profile, so
    normal Chrome must already be closed. The dedicated and copied-profile modes
    use separate user-data directories.
    """
    cdp_url = cdp_url_for_port(config.cdp_port)
    if debugger_is_ready(cdp_url=cdp_url):
        print(f"   Reusing Chrome remote debugging endpoint at {cdp_url}")
        prepare_debugger_page(cdp_url=cdp_url, target_url=config.initial_url)
        return cdp_url

    user_data_dir = chrome_user_data_dir(
        config.chrome_profile,
        config.chrome_user_data_dir,
    )
    if (
        config.chrome_profile == ChromeProfileMode.USER_DEFAULT.value
        and config.chrome_user_data_dir is None
    ):
        raise RuntimeError(
            "Chrome blocks remote debugging on the literal default user profile. "
            "Use --chrome-profile default for FlyingPig's persistent copied profile, "
            "or pass --chrome-user-data-dir with a non-default Chrome profile."
        )
    if (
        config.chrome_profile == ChromeProfileMode.DEFAULT_COPY.value
        and config.chrome_user_data_dir is None
    ):
        ensure_default_profile_copy(user_data_dir)
    user_data_dir.mkdir(parents=True, exist_ok=True)

    command = [
        CHROME_APP,
        "--remote-debugging-address=127.0.0.1",
        f"--remote-debugging-port={config.cdp_port}",
        f"--user-data-dir={user_data_dir}",
        "--profile-directory=Default",
        "--new-window",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-component-extensions-with-background-pages",
        f"--window-size={config.window_width},{config.window_height}",
        f"--window-position={config.window_left},{config.window_top}",
        config.initial_url,
    ]
    if config.disable_extensions:
        command.insert(-1, "--disable-extensions")

    print("   Launching visible Flying Pig work window with remote debugging.")
    print(f"   Profile dir: {user_data_dir}")
    subprocess.Popen(command, start_new_session=True)
    wait_for_debugger(cdp_url=cdp_url)
    if config.dashboard_url:
        open_dashboard_tab(
            cdp_url=cdp_url,
            dashboard_url=config.dashboard_url,
            target_url=config.initial_url,
        )
    return cdp_url


def prepare_debugger_page(
    *,
    target_url: str,
    port: int | None = None,
    cdp_url: str | None = None,
) -> None:
    """Reset a reused CDP work window to one task page.

    Chrome keeps old tabs alive when we reconnect to an existing debugging
    endpoint. A fresh launch request should not let stale Oura/Uber/etc. pages
    become the next run target, so create the requested page, activate it, and
    close the previous page targets.
    """
    base_url = _cdp_base_url(port=port, cdp_url=cdp_url)
    targets = debugger_targets(cdp_url=base_url) or []
    page_targets = [target for target in targets if target.get("type") == "page"]
    if len(page_targets) == 1 and str(page_targets[0].get("url", "")) == target_url:
        return

    new_target_id = open_debugger_page(cdp_url=base_url, url=target_url)
    if not new_target_id:
        return
    activate_debugger_target(cdp_url=base_url, target_id=new_target_id)
    for target in page_targets:
        old_target_id = target.get("id")
        if old_target_id and old_target_id != new_target_id:
            close_debugger_target(cdp_url=base_url, target_id=old_target_id)


def open_debugger_page(
    *,
    url: str,
    port: int | None = None,
    cdp_url: str | None = None,
) -> str | None:
    base_url = _cdp_base_url(port=port, cdp_url=cdp_url)
    encoded_url = urllib.parse.quote(url or "about:blank", safe="")
    try:
        request = urllib.request.Request(
            f"{base_url}/json/new?{encoded_url}",
            method="PUT",
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            payload = json.load(response)
        return payload.get("id")
    except (OSError, urllib.error.URLError, ValueError):
        return None


def activate_debugger_target(
    *,
    target_id: str,
    port: int | None = None,
    cdp_url: str | None = None,
) -> None:
    base_url = _cdp_base_url(port=port, cdp_url=cdp_url)
    try:
        urllib.request.urlopen(
            f"{base_url}/json/activate/{target_id}",
            timeout=2,
        ).close()
    except (OSError, urllib.error.URLError):
        return


def close_debugger_target(
    *,
    target_id: str,
    port: int | None = None,
    cdp_url: str | None = None,
) -> None:
    base_url = _cdp_base_url(port=port, cdp_url=cdp_url)
    try:
        urllib.request.urlopen(
            f"{base_url}/json/close/{target_id}",
            timeout=2,
        ).close()
    except (OSError, urllib.error.URLError):
        return


def open_dashboard_tab(
    *,
    dashboard_url: str,
    target_url: str,
    port: int | None = None,
    cdp_url: str | None = None,
) -> None:
    """Open dashboard status beside the task tab, then reactivate task tab."""
    base_url = _cdp_base_url(port=port, cdp_url=cdp_url)
    try:
        task_target_id = find_debugger_target_id(cdp_url=base_url, url_prefix=target_url)
        encoded_dashboard_url = urllib.parse.quote(dashboard_url, safe="")
        request = urllib.request.Request(
            f"{base_url}/json/new?{encoded_dashboard_url}",
            method="PUT",
        )
        urllib.request.urlopen(request, timeout=2).close()
        if task_target_id:
            urllib.request.urlopen(
                f"{base_url}/json/activate/{task_target_id}",
                timeout=2,
            ).close()
        print(f"   Dashboard tab: {dashboard_url}")
    except (OSError, urllib.error.URLError) as exc:
        print(f"   Dashboard tab could not be opened automatically: {exc}")


def find_debugger_target_id(
    *,
    url_prefix: str,
    port: int | None = None,
    cdp_url: str | None = None,
) -> str | None:
    base_url = _cdp_base_url(port=port, cdp_url=cdp_url)
    info = debugger_page_info(cdp_url=base_url)
    if info and str(info.get("url", "")).startswith(url_prefix):
        return info.get("id")

    targets = debugger_targets(cdp_url=base_url)
    if targets is None:
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
            "Flying Pig work window alongside your current Chrome."
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
