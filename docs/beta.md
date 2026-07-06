# Flying Pig Beta Checklist

## Beta Scope

- Site: American Express.
- UX: Native desktop shell with the helper-served dashboard as the single cockpit, supervising a local helper sidecar and a separate Flying Pig work window.
- User mode: supervised only. The user keeps the Amex tab visible and answers mid-run questions.
- Initial playbooks: general support, benefit/credit follow-up, dispute charge.

## Install Flow

For public Mac beta users, use the packaged desktop app:

1. Download the latest `Flying-Pig-*-arm64-mac.zip` from
   `https://github.com/lifan-builds/flyingpig/releases`.
2. Unzip it and open `Flying Pig.app`.
3. If macOS blocks the unsigned beta, approve it from **System Settings ->
   Privacy & Security** and open the app again.
4. In the first-run model setup panel, choose a provider and save an API key.
5. Click **Open Work Window**.
6. In the Flying Pig work window, prepare the Amex customer-service tab.
7. Confirm the task and supervise the run.

For development builds, install the Python package in editable/dev mode:

   ```bash
   pip install -e ".[dev]"
   playwright install
   ```

Then start the desktop app:

   ```bash
   npm install
   npm run desktop:dev
   ```

   The desktop app starts the helper automatically, waits for `/health`, and
   loads the dashboard.

For supervised live sessions, start the run from the desktop app. Live chats
often require Decision Checkpoints, verification prompts, or settlement choices;
the app keeps the run alive while the user answers.

The dashboard has separate helper and work-window statuses. **Helper Online**
means the local helper is reachable; **Work Window Connected** means the
controlled Chrome debugging endpoint is reachable. The dashboard tab is the
cockpit, not the browser-use work area.

The beta default is a dedicated Flying Pig work profile that can run
beside normal Chrome and persists its own login state. The copied-profile path
remains available through the work-window profile picker.

Helper/API/CLI entry points remain available for development and service testing
only; they are not beta user paths:

```bash
flyingpig-helper
flyingpig-helper --open-dashboard
python scripts/start.py --help
python scripts/daemon.py --help
```

## Build Release Bundle

Create a local beta zip:

```bash
python scripts/build_beta_release.py --clean
```

The bundle includes the desktop shell source, helper code, helper-served dashboard, prompts, README, and beta install guide.

Create a development desktop build path:

```bash
npm run build:helper
npm run desktop:package
```

The helper sidecar is produced with PyInstaller and bundled into the Electron
app as an extra resource. The current macOS package target is `.zip`; DMG
packaging is deferred until the local native-addon signing issue in the DMG
license toolchain is resolved. The release must be scanned before publishing for
PII, API keys, credentials, tokens, cookies, logs, recordings, and user-specific
account data.

## Pre-Beta Gates

- `ruff check src scripts tests` passes.
- `pytest tests -q -m "not slow"` passes.
- `npm run test:dashboard` passes.
- `npm run test:desktop` passes.
- `python scripts/build_beta_release.py --clean` produces `dist/flyingpig-beta-1.0.1.zip`.
- The built zip is scanned for PII, API keys, credentials, tokens, cookies, logs, recordings, and user-specific account information before publishing.
- A supervised Amex smoke reaches chat, sends only after user confirmation, and captures a transcript.
- Cancel from the dashboard stops an active run.
- Helper-offline state in the dashboard clearly offers setup and reconnect paths.
- Open Work Window from the dashboard returns a CDP endpoint and opens the Amex page in an extension-free controlled window.
- Start is disabled when the helper is online but controlled Chrome is not connected.
- Start is disabled when the selected model is not configured.
- The first-run dashboard path exposes model setup, work-window launch, chat-surface preparation, editable task brief, and local PII-free activation signals.
- Relaunching the work window against an already-running CDP endpoint resets the task page and closes stale page targets.

## Release Evidence — 2026-05-24

Automated gates:

| Gate | Evidence |
| --- | --- |
| Ruff | `ruff check src scripts tests` passed. |
| Non-slow tests | `pytest tests -q -m "not slow"` passed: 138 passed, 2 deselected. |
| Dashboard smoke | Elevated `npm run test:dashboard` passed with benchmark output: `helper_online=1828ms`, `work_window_ready=2052ms`, `mock_run_done=2199ms`. |
| Desktop smoke | Elevated `npm run test:desktop` passed; Electron shell reached the helper-served dashboard at `http://127.0.0.1:8865/dashboard/`. |
| Source release bundle | `python scripts/build_beta_release.py` produced `dist/flyingpig-beta-1.0.1.zip`; final SHA-256 should be computed after docs are finalized because the release bundle includes this checklist. |
| Packaged helper sidecar | `npm run build:helper` produced `dist/helper/flyingpig-helper`. PyInstaller completed with optional-backend/cache warnings only. |
| Desktop package | `npm run desktop:package` produced `dist/desktop/Flying Pig-1.0.1-arm64-mac.zip`; SHA-256 `fef65229976165d5665782510a049a8ca44dc78a6d5eaafbe2bc0ed8f6159c48`. The app is unsigned because no local Developer ID identity is configured. |
| Release privacy scan | `zipgrep`/filename scans found no common API-key/private-key patterns, emails, `.env`, cookies, logs, recordings, databases, or legacy `extension/` and `frontend/` paths in the 1.0.1 source bundle or desktop zip. |

## Release Evidence — 2026-05-18

Automated gates:

| Gate | Evidence |
| --- | --- |
| Focused backend/browser tests | `pytest tests/unit/test_browser_runtime.py tests/unit/test_daemon_server.py -q` passed: 22 passed. |
| Focused lint | `ruff check src/agent/browser_runtime.py src/daemon/server.py src/daemon/run_session.py tests/unit/test_browser_runtime.py tests/unit/test_daemon_server.py` passed. |
| Dashboard protocol | `node scripts/test_dashboard_protocol.mjs` passed. |
| Dashboard smoke | Elevated `npm run test:dashboard` passed after reinstalling root and frontend Node dependencies. |
| Beta bundle | `python scripts/build_beta_release.py --clean` produced `dist/flyingpig-beta-0.1.0.zip` (104K). |
| Release privacy scan | `zipgrep` found no common API-key/private-key patterns, local user paths, cookie/log/recording indicators, or known live-run PII strings in the beta zip. |

Manual dashboard pass:

- Opened the desktop app, which loaded the helper-served dashboard, and verified **Helper Online** with **Work Window Offline**.
- Verified **Start** is disabled until the controlled work window is connected.
- Clicked **Open Work Window**; dashboard switched to **Work Window Connected**, changed the URL label to **Work Window URL**, and followed the Oura support URL from the controlled work window rather than the dashboard URL.
- Relaunched while CDP was already running; CDP inspection showed one debuggable `page` target for the Oura support page after stale page cleanup.

## Release Evidence — 2026-05-19

Automated gates:

| Gate | Evidence |
| --- | --- |
| Ruff | `ruff check src scripts tests` passed. |
| Non-slow tests | `pytest tests -q -m "not slow"` passed: 123 passed, 2 deselected. |
| Dashboard smoke | Elevated `npm run test:dashboard` passed. The smoke drives the helper-served `/dashboard/` UI directly, not an unpacked extension. |
| Beta bundle | `python scripts/build_beta_release.py --clean` produced `dist/flyingpig-beta-0.1.0.zip`; package contents include `dashboard/` and no `extension/`. |
| Release privacy scan | `zipgrep` found no common API-key/private-key patterns, known live-run PII strings, cookie/log/recording indicators, or user-specific account information. |
| CLIProxy mock agent run | `python scripts/run_mock_amex.py --headless --model cliproxyapi --max-steps 18 --llm-timeout 240 --save-dir recordings/mock_run` passed using `gpt-5.5`, accepted a `$50` credit, and captured confirmation `MOCK-12345`. |

External chat-surface smoke:

- LiveChat and Olark loaded, exposed visible chat widgets, and accepted harmless draft text without submitting.
- Several other public sites exposed support/product links that look like chat by text alone; use browser-use's visual/model loop for chat-surface selection rather than deterministic text-only matching.
- Full live LLM-driven external-site agent runs were not submitted to public sites; the CLIProxy-powered LLM run was verified against the local mock Amex server.

## Release Evidence — 2026-05-15

Automated gates:

| Gate | Evidence |
| --- | --- |
| Ruff | `ruff check src scripts tests` passed. |
| Non-slow tests | `pytest tests -q -m "not slow"` passed: 116 passed, 2 deselected. |
| Dashboard smoke | `npm run test:dashboard` passed after granting local-port/Chromium permission. The smoke covers helper-offline setup/reconnect, disabled Start before Work Window Connected, Open Work Window, start/result, cancel, Decision Checkpoint option rendering after dashboard reload, and checkpoint answer submission. |
| Beta bundle | `python scripts/build_beta_release.py --clean` produced `dist/flyingpig-beta-0.1.0.zip`. |
| Release privacy scan | Removed a hardcoded JWT secret from `src/api/auth.py` and a local editable path from `requirements.txt`, rebuilt the zip, and verified no common API-key/private-key patterns, emails, card-number-like digit sequences, known live-run PII strings, logs, recordings, cookies, or local user paths are present. |

Helper service smoke:

| Step | Evidence |
| --- | --- |
| Initial stale service recovery | Before reinstall, `flyingpig-macos-helper start` found a stale installed plist that was not loaded in launchd and reported `launchctl kickstart` status 113. The CLI now reports this as a recovery-focused helper error instead of a Python traceback. |
| `flyingpig-macos-helper install` | Reinstalled `~/Library/LaunchAgents/com.flyingpig.helper.plist` and started the helper. |
| `flyingpig-macos-helper status` | Shows `com.flyingpig.helper` in `state = running` after install/start. |
| Helper health | `curl http://127.0.0.1:8765/health` returned `{"ok":true,"sites":["amex","generic","oura"]}` while running. |
| `flyingpig-macos-helper stop` | Fixed the stop command to boot out `gui/<uid>/com.flyingpig.helper` and fail loudly if launchctl refuses. Verified the helper reports not running and `/health` fails after stop. |
| `flyingpig-macos-helper start` | Restarted the installed helper; status returned to `state = running` and `/health` responded again. |

Manual supervised Amex smoke status:

- Not completed in this run because it requires the first-cohort tester to be present in the dashboard with Amex login/MFA completed and explicit confirmation before the agent sends the first message.
- Prepared smoke path: open the desktop app, click **Open Work Window**, prepare Amex chat in the extension-free work window, enter the task, verify the agent performs Chat Surface Check, approve any consequential outbound message, then verify the result includes transcript path, outcome, failure stage if any, and human-escalation status.
- If blocked, record the blocker with the visible stage: helper setup, work-window launch, Amex login/MFA, Chat Surface Check, send confirmation, live chat/human escalation, cancel, or evidence capture.

Full mock-agent dashboard smoke status:

- The committed dashboard smoke is still deterministic mock-daemon/browser protocol coverage rather than a full browser-use `AgentBrain` run from the dashboard.
- Current blocker: a full dashboard-driven mock-agent run needs a deterministic browser-use LLM or a configured live LLM provider, plus a CDP work window started separately from the dashboard test browser. Running it unconditionally in `npm run test:dashboard` would make the release gate depend on external model credentials and a second debuggable Chrome process.
- Existing coverage that reduces the risk: slow `tests/e2e/test_mock_chat.py` exercises `AgentBrain` against the mock Amex site when an LLM/browser environment is available; unit daemon tests cover reconnectable Decision Checkpoint snapshots; the dashboard smoke covers the dashboard/helper protocol and release UX states.

## Beta Operating Rules

- Do not store Amex credentials.
- Do not publish release artifacts that contain PII, API keys, credentials, tokens, cookies, logs, recordings, or user-specific account information.
- Do not ask the agent to make irreversible account changes without explicit user confirmation.
- Review every first-cohort transcript before expanding access.
- Record outcome, failure stage, transcript path, and whether human escalation succeeded.
