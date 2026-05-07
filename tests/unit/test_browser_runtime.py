from pathlib import Path

from src.agent.browser_runtime import (
    ChromeLaunchConfig,
    chrome_user_data_dir,
    find_debugger_target_id,
    launch_cdp_chrome,
    open_dashboard_tab,
)


def test_chrome_user_data_dir_uses_custom_dir():
    assert chrome_user_data_dir("default", "~/custom-chrome") == Path(
        "~/custom-chrome"
    ).expanduser()


def test_chrome_user_data_dir_uses_existing_profile(monkeypatch, tmp_path):
    existing = tmp_path / "Chrome"
    monkeypatch.setattr(
        "src.agent.browser_runtime.DEFAULT_CHROME_USER_DATA_DIR",
        existing,
    )

    assert chrome_user_data_dir("existing", None) == existing


def test_launch_cdp_chrome_reuses_ready_debugger(monkeypatch):
    monkeypatch.setattr("src.agent.browser_runtime.debugger_is_ready", lambda port: True)

    cdp_url = launch_cdp_chrome(ChromeLaunchConfig(cdp_port=9333))

    assert cdp_url == "http://127.0.0.1:9333"


def test_chrome_launch_config_defaults_to_copied_user_profile():
    config = ChromeLaunchConfig()

    assert config.chrome_profile == "default"
    assert config.dashboard_url is None


def test_launch_cdp_chrome_can_launch_dedicated_while_regular_chrome_runs(monkeypatch):
    launched = {}

    monkeypatch.setattr("src.agent.browser_runtime.debugger_is_ready", lambda port: False)
    monkeypatch.setattr("src.agent.browser_runtime.regular_chrome_is_running", lambda: True)
    monkeypatch.setattr("src.agent.browser_runtime.wait_for_debugger", lambda port: None)
    monkeypatch.setattr("pathlib.Path.mkdir", lambda self, parents=False, exist_ok=False: None)

    class FakePopen:
        def __init__(self, command, **kwargs):
            launched["command"] = command
            launched["kwargs"] = kwargs

    monkeypatch.setattr("src.agent.browser_runtime.subprocess.Popen", FakePopen)

    cdp_url = launch_cdp_chrome(ChromeLaunchConfig(cdp_port=9444))

    assert cdp_url == "http://127.0.0.1:9444"
    assert any("--remote-debugging-port=9444" in arg for arg in launched["command"])
    assert launched["kwargs"] == {"start_new_session": True}


def test_launch_cdp_chrome_opens_dashboard_tab(monkeypatch, tmp_path):
    calls = []

    monkeypatch.setattr("src.agent.browser_runtime.debugger_is_ready", lambda port: False)
    monkeypatch.setattr("src.agent.browser_runtime.wait_for_debugger", lambda port: None)
    monkeypatch.setattr("src.agent.browser_runtime.ensure_default_profile_copy", lambda path: None)
    monkeypatch.setattr("pathlib.Path.mkdir", lambda self, parents=False, exist_ok=False: None)
    monkeypatch.setattr(
        "src.agent.browser_runtime.open_dashboard_tab",
        lambda **kwargs: calls.append(kwargs),
    )

    class FakePopen:
        def __init__(self, command, **kwargs):
            pass

    monkeypatch.setattr("src.agent.browser_runtime.subprocess.Popen", FakePopen)

    launch_cdp_chrome(
        ChromeLaunchConfig(
            cdp_port=9777,
            chrome_user_data_dir=str(tmp_path),
            initial_url="https://example.com/chat",
            dashboard_url="http://127.0.0.1:8000",
        )
    )

    assert calls == [
        {
            "port": 9777,
            "dashboard_url": "http://127.0.0.1:8000",
            "target_url": "https://example.com/chat",
        }
    ]


def test_launch_cdp_chrome_refuses_literal_existing_profile(monkeypatch):
    monkeypatch.setattr("src.agent.browser_runtime.debugger_is_ready", lambda port: False)

    try:
        launch_cdp_chrome(ChromeLaunchConfig(chrome_profile="existing"))
    except RuntimeError as exc:
        assert "blocks remote debugging" in str(exc)
    else:
        raise AssertionError("Expected literal existing-profile guard to raise")


def test_launch_cdp_chrome_uses_custom_existing_profile(
    monkeypatch,
    tmp_path,
):
    launched = {}

    monkeypatch.setattr("src.agent.browser_runtime.debugger_is_ready", lambda port: False)
    monkeypatch.setattr("src.agent.browser_runtime.wait_for_debugger", lambda port: None)
    custom_profile = tmp_path / "Chrome"

    class FakePopen:
        def __init__(self, command, **kwargs):
            launched["command"] = command
            launched["kwargs"] = kwargs

    monkeypatch.setattr("src.agent.browser_runtime.subprocess.Popen", FakePopen)

    cdp_url = launch_cdp_chrome(
        ChromeLaunchConfig(
            chrome_profile="existing",
            chrome_user_data_dir=str(custom_profile),
            cdp_port=9555,
        )
    )

    assert cdp_url == "http://127.0.0.1:9555"
    assert f"--user-data-dir={custom_profile}" in launched["command"]


def test_launch_cdp_chrome_refuses_first_default_copy_when_regular_chrome_runs(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr("src.agent.browser_runtime.debugger_is_ready", lambda port: False)
    monkeypatch.setattr("src.agent.browser_runtime.regular_chrome_is_running", lambda: True)
    default_profile = tmp_path / "Chrome"
    default_profile.mkdir()
    monkeypatch.setattr(
        "src.agent.browser_runtime.DEFAULT_CHROME_USER_DATA_DIR",
        default_profile,
    )
    monkeypatch.setattr(
        "src.agent.browser_runtime.DEFAULT_COPY_CHROME_USER_DATA_DIR",
        tmp_path / "missing-copy",
    )

    try:
        launch_cdp_chrome(ChromeLaunchConfig(chrome_profile="default"))
    except RuntimeError as exc:
        assert "Quit normal Chrome once" in str(exc)
    else:
        raise AssertionError("Expected first default-copy guard to raise")


def test_open_dashboard_tab_opens_new_tab_then_reactivates_task(monkeypatch):
    opened = []
    monkeypatch.setattr(
        "src.agent.browser_runtime.find_debugger_target_id",
        lambda **kwargs: "task-target",
    )

    class FakeResponse:
        def close(self):
            pass

    def fake_urlopen(request, timeout=0):
        opened.append(request.full_url if hasattr(request, "full_url") else request)
        return FakeResponse()

    monkeypatch.setattr("src.agent.browser_runtime.urllib.request.urlopen", fake_urlopen)

    open_dashboard_tab(
        port=9222,
        dashboard_url="http://127.0.0.1:8000",
        target_url="https://example.com/chat",
    )

    assert opened == [
        "http://127.0.0.1:9222/json/new?http%3A%2F%2F127.0.0.1%3A8000",
        "http://127.0.0.1:9222/json/activate/task-target",
    ]


def test_find_debugger_target_id_matches_page_prefix(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def read(self):
            return (
                b'[{"id":"one","type":"page","url":"https://example.com/chat/start"},'
                b'{"id":"two","type":"other","url":"https://example.com/chat"}]'
            )

    monkeypatch.setattr(
        "src.agent.browser_runtime.urllib.request.urlopen",
        lambda *args, **kwargs: FakeResponse(),
    )

    assert (
        find_debugger_target_id(port=9222, url_prefix="https://example.com/chat")
        == "one"
    )
