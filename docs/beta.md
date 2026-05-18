# Flying Pig Beta Checklist

## Beta Scope

- Site: American Express.
- UX: Chrome dashboard tab as the single cockpit, controlling the local helper service and a separate Flying Pig work window.
- User mode: supervised only. The user keeps the Amex tab visible and answers mid-run questions.
- Initial playbooks: general support, benefit/credit follow-up, dispute charge.

## Install Flow

1. Install the Python package in editable/dev mode for the first beta cohort:

   ```bash
   pip install -e ".[dev]"
   playwright install
   ```

2. Install the macOS helper service:

   ```bash
   flyingpig-macos-helper install
   ```

3. Load `extension/` as an unpacked Chrome extension.
4. Open the Flying Pig dashboard and click **Launch Work Window**.
5. In the FlyingPig work window, prepare the Amex customer-service tab.
6. Confirm the task and supervise the run.

The dashboard has separate helper and work-window statuses. **Helper Online**
means the local helper is reachable; **Work Window Connected** means the
controlled Chrome debugging endpoint is reachable. The dashboard tab is the
cockpit, not the browser-use work area.

The beta default is a dedicated Flying Pig work profile that can run
beside normal Chrome and persists its own login state. The copied-profile
path remains available for testing with `flyingpig-helper --chrome-profile
default`.

Support commands:

```bash
flyingpig-macos-helper status
flyingpig-macos-helper stop
flyingpig-macos-helper start
flyingpig-macos-helper uninstall
```

## Build Release Bundle

Create a local beta zip:

```bash
python scripts/build_beta_release.py --clean
```

The bundle includes the helper code, prompts, Chrome extension, README, and beta install guide.

## Pre-Beta Gates

- `ruff check src scripts tests` passes.
- `pytest tests -q -m "not slow"` passes.
- `npm run test:extension` passes.
- `python scripts/build_beta_release.py --clean` produces `dist/flyingpig-beta-0.1.0.zip`.
- The built zip is scanned for PII, API keys, credentials, tokens, cookies, logs, recordings, and user-specific account information before publishing.
- `flyingpig-macos-helper status` shows the helper running after install.
- A supervised Amex smoke reaches chat, sends only after user confirmation, and captures a transcript.
- Cancel from the dashboard stops an active run.
- Helper-offline state in the dashboard clearly offers setup and reconnect paths.
- Launch Work Window from the dashboard returns a CDP endpoint and opens the Amex page in an extension-free controlled window.
- Start is disabled when the helper is online but controlled Chrome is not connected.

## Release Evidence — 2026-05-15

Automated gates:

| Gate | Evidence |
| --- | --- |
| Ruff | `ruff check src scripts tests` passed. |
| Non-slow tests | `pytest tests -q -m "not slow"` passed: 116 passed, 2 deselected. |
| Extension smoke | `npm run test:extension` passed after granting local-port/Chromium permission. The smoke covers helper-offline setup/reconnect, disabled Start before Work Window Connected, Launch Work Window, start/result, cancel, Decision Checkpoint option rendering after dashboard reload, and checkpoint answer submission. |
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
- Prepared smoke path: install helper, load extension, open the dashboard in normal Chrome, click **Launch Work Window**, prepare Amex chat in the extension-free work window, enter the task, verify the agent performs Chat Surface Check, approve the first outbound message, then verify the result includes transcript path, outcome, failure stage if any, and human-escalation status.
- If blocked, record the blocker with the visible stage: helper setup, work-window launch, Amex login/MFA, Chat Surface Check, send confirmation, live chat/human escalation, cancel, or evidence capture.

Full mock-agent extension smoke status:

- The committed extension smoke is still deterministic mock-daemon/browser protocol coverage rather than a full browser-use `AgentBrain` run from the dashboard.
- Current blocker: a full dashboard-driven mock-agent run needs a deterministic browser-use LLM or a configured live LLM provider, plus a CDP work window started separately from the extension test browser. Running it unconditionally in `npm run test:extension` would make the release gate depend on external model credentials and a second debuggable Chrome process.
- Existing coverage that reduces the risk: slow `tests/e2e/test_mock_chat.py` exercises `AgentBrain` against the mock Amex site when an LLM/browser environment is available; unit daemon tests cover reconnectable Decision Checkpoint snapshots; the extension smoke covers the dashboard/helper protocol and release UX states.

## Beta Operating Rules

- Do not store Amex credentials.
- Do not publish release artifacts that contain PII, API keys, credentials, tokens, cookies, logs, recordings, or user-specific account information.
- Do not ask the agent to make irreversible account changes without explicit user confirmation.
- Review every first-cohort transcript before expanding access.
- Record outcome, failure stage, transcript path, and whether human escalation succeeded.
