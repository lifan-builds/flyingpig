# Findings

See archived `FINDINGS.md` (if retained) for research on DoNotPay, browser-use, Playwright vs Puppeteer, FTC/legal landscape, and industry predictions (Gartner/Forrester/CNBC 2026).

### 2026-07-05 Installed work-window CDP conflict
- The running desktop app is the packaged local build at `dist/desktop/mac-arm64/Flying Pig.app`; no `/Applications/Flying Pig.app` install was found in this session.
- The helper is healthy on `127.0.0.1:8765`, but Open Work Window fails because normal Chrome owns IPv4 `127.0.0.1:9222` and returns 404 for `/json/version`, while the Flying Pig work Chrome falls back to IPv6 `[::1]:9222` and logs `bind() failed: Address already in use (48)` followed by `DevTools listening on ws://[::1]:9222/...`.
- The helper/dashboard status path collapses any `cdp_url` to `http://127.0.0.1:<port>` and therefore reports Work Window Offline even when `http://localhost:9222/json/version` and `http://[::1]:9222/json` expose debuggable Flying Pig pages.
- Direct Chrome debugging is viable: launching Chrome with a separate profile and `--remote-debugging-address=127.0.0.1 --remote-debugging-port=9335` produced a usable CDP endpoint, and the installed helper returned `connected:true` for `/browser/status?cdp_url=http://127.0.0.1:9335`.
- Implemented follow-up: source dashboard/helper now add a non-destructive **Connect Existing Chrome** flow through `POST /browser/attach`; CDP helpers preserve full endpoint hosts (`localhost`, `127.0.0.1`, `[::1]`), dashboard launch parses the CDP port from the Browser endpoint field, and attach failures explain how to start Chrome with `--remote-debugging-port`. Remaining optional hardening: richer port-owner diagnostics.

### 2026-07-05 Chrome DevTools MCP auto-connect
- User provided the Claude Code mechanism for controlling an existing Chrome session: `chrome-devtools-mcp@latest --autoConnect` registered as `chrome-devtools`, with Chrome permission enabled at `chrome://inspect/#remote-debugging`. Before permission, MCP can fail with missing `DevToolsActivePort`; after permission, `list_pages` returns existing tabs and `take_snapshot` verifies an inspectable selected page.
- Implemented source support for a helper-owned MCP auto-connect path without depending on Claude Code's personal MCP config: new `src/agent/chrome_devtools_mcp.py` starts `npx -y chrome-devtools-mcp@latest --autoConnect`, initializes MCP over stdio, calls `list_pages`, `select_page`, and `take_snapshot`, parses safe tab metadata, and maps missing permission/Node errors to actionable copy.
- Added FastAPI endpoints `POST /browser/mcp/connect`, `GET /browser/mcp/pages`, and `POST /browser/mcp/select`. These list real existing Chrome tabs, select/snapshot a user-chosen tab, and only claim browser-use readiness if MCP page metadata exposes a usable CDP handoff URL.
- Added dashboard **Auto-Connect Existing Chrome** UI with a real-tab warning/picker. If CDP handoff is available, it populates `#cdpUrl`, marks Work Window Connected, and reuses the existing browser-use run path. If not, it reports that MCP inspection works but this build still needs a browser-use-compatible CDP URL.
- Verification passed: `ruff check src tests`; `pytest tests/unit/test_chrome_devtools_mcp.py tests/unit/test_daemon_server.py -q` (30 passed); `pytest tests/unit -q` (128 passed); `node scripts/test_dashboard_protocol.mjs`; `npm run test:dashboard`; `node --check dashboard/dashboard.js scripts/test_helper_dashboard.mjs`; `git diff --check`.
- Minimal real existing-Chrome MCP smoke passed after switching MCP stdio framing to newline-delimited JSON and using `select_page`'s `pageId` argument with `bringToFront:false`. `list_pages` returned 6 existing Chrome tabs (including local CLIProxy/CPA pages and Linear tabs), selecting a safe localhost tab succeeded, and `take_snapshot` produced `snapshot_available:true`. The MCP response did not expose a CDP handoff URL, so Flying Pig correctly reported inspection-only mode for browser-use execution.

### 2026-05-25 Public beta first-run readiness
- Broader-audience beta readiness should optimize for the first 10 minutes: install/open, model setup, work-window launch, chat-surface preparation, task brief, and supervised start.
- Model/API-key setup was already implemented but lived under Advanced, which made it too easy for new users to miss. It should be part of the primary first-run surface while low-level endpoints and manual agent approach remain Advanced.
- Start readiness should treat an unconfigured selected model as a blocker before a live run starts. This avoids sending new users into a model failure after they already prepared the work window.
- First-success measurement should stay local and PII-free: coarse activation signals such as model configured, work window opened, chat surface selected, first run started, checkpoint answered, human reached, and outcome marked are acceptable; raw chat text, private URLs, credentials, cookies, and account details are not.

### 2026-05-05 Amex live-flow handoff
- User-facing live task is the Amex Oura Ring wellness-credit request for Morgan Stanley Platinum ending 81004; the script must run in the foreground so CLI `ask_user` prompts can read stdin.
- The exact previous live failure was `AttributeError: 'Page' object has no attribute 'url'` in `ChatNavigator.wait_for_login()`; fixed by using browser-use wrapper methods: `await page.get_url()` and `await page.goto(...)`.
- Added regression coverage in `tests/integration/test_brain_integration.py` for `wait_for_login()` using browser-use-style page methods.
- Mock e2e now starts from `?logged_in=true` to match the real flow after manual login and returns confirmation `MOCK-12345` so the agent can finish deterministically.
- Verification evidence after fixes: focused lint passed for changed files; focused tests passed (`tests/integration/test_brain_integration.py` + `tests/e2e/test_mock_chat.py`, 16 passed); full lint passed; full pytest passed earlier with 68 passed before the final CLI-error hardening edits; system-Chrome `scripts/demo_amex.py --launch-smoke` reached Amex customer-service URL/title after Chrome was available.
- Not yet verified after the very last edits because the user stopped before final full `pytest tests/`, `scripts/demo_amex.py --dry-run`, and `flyingpig run ... --dry-run` could be rerun.

### 2026-05-06 Mock Amex system-Chrome run
- CLIProxy path is healthy: browser-use logged provider `openai` and model `gpt-5.5`; earlier slowness came from browser-use state/screenshot handling, not the model endpoint.
- Added direct chat transcript capture because browser-use's judge can miss delayed chat DOM evidence and false-fail despite the transcript showing the offer and confirmation.
- System Chrome runs must start with regular Chrome closed. If a normal Chrome window is already open, browser-use can create/drive a copied-profile Chrome target while Computer Use keeps seeing the old normal Chrome window.
- Completed mock transcript: user asked to cancel generic Amex Platinum, mock offered `$50` statement credit, agent accepted, mock returned confirmation `MOCK-12345`.
- Remaining visual quirk: even after local `--app=<mock-url>` launch and extension disabling, macOS/Computer Use may still expose a `New Tab` top-chrome window while browser-use operates the mock target. Treat transcript/session artifacts as verification unless a future change specifically fixes macOS window exposure.

### 2026-05-06 Live Amex Oura/CDP run
- Computer Use and browser-use can inspect the same live Amex window when Chrome is launched as a single visible remote-debugging window and regular Chrome is closed first.
- Chrome refused remote debugging against the literal default user-data directory; `scripts/start.py --chrome-profile default` now uses a persistent copy at `~/.flyingpig/chrome-cdp-default-copy`.
- The copied profile carried enough state for the user to log in and the agent to attach to `global.americanexpress.com/overview`; Computer Use verified the same visible window and the Morgan Stanley Platinum ending 81004 context.
- The Amex chat widget persisted prior Oura history, including a prior denial, so the prompt's read-only-history rule remains essential.
- Live run evidence: the agent sent a fresh Oura wellness-credit request, reached human rep Dwight, and asked for manual/courtesy credit or re-review; the rep began reviewing the account.
- Run failed operationally because CLIProxy `gpt-5.5` entered provider cooldown mid-chat with no fallback LLM configured. Session artifact: `recordings/session_american_express_20260506_042839.json`.
- After browser-use detached, Computer Use again switched to another Chrome/New Tab surface. For monitoring during the run, Computer Use was useful only while the CDP Chrome was the sole active Chrome surface and the agent was still attached.

### 2026-05-06 Live Amex Oura task handoff
- Current real task is not annual-fee negotiation. It is an Amex/Oura benefit-credit request and must not use the annual-fee negotiation template.
- Record the two purchase/card lines exactly for the next live run:
  - Morgan Stanley Platinum Card ending 81004 — Apr 18 — `PAYPAL *OURARING 8333630010 CA` — `$215.00`
  - Platinum Card ending 71009 — Apr 18 — `PAYPAL *OURARING 8333630010 CA` — `$215.06`
- The agent should ask Amex one item at a time:
  1. Ask about the Amex credit first.
  2. Then ask about the Oura Ring credit.
- Keep the prompt scoped to benefit/reimbursement review, manual courtesy credit, or re-review. Do not drift into retention, cancellation, or annual-fee waiver unless the user explicitly changes the task.

### 2026-05-06 Live Amex Oura 71009 run
- User corrected the scope before messaging Amex: Morgan Stanley Platinum ending 81004 had already received its credit and should not be discussed further.
- FlyingPig attached to the copied-profile debug Chrome at `http://127.0.0.1:9222`, verified chat readiness, asked for user confirmation, then messaged Amex only about Platinum ending 71009.
- Target transaction: Platinum Card ending 71009 — Apr 18 — `PAYPAL *OURARING 8333630010 CA` — `$215.06`.
- Human representative Mitchell handled the chat. He initially reiterated the direct-ouraring.com/ring-only eligibility rule, then after clarification stated that he manually submitted a `$200` credit request and that it should post in 5 working days.
- FlyingPig asked for a reference/confirmation number, but none was visible/provided before finalization.
- Session artifact: `recordings/session_american_express_20260507_014129.json`.

### 2026-05-06 Live-run observations and improvements
- What worked:
  - CDP attach eventually recovered from the initial `chrome://omnibox-popup.top-chrome/` target by switching to the real Amex overview tab.
  - Mandatory pre-flight confirmation prevented the stale two-card task from being sent after the user corrected scope to only Platinum ending 71009.
  - The agent stayed on topic, identified Mitchell as a human, waited while he reviewed, handled the policy objection, and obtained a `$200` manual credit request.
- What to improve:
  - The agent used many repeated 10-second waits early in the chat. Human support chats need fewer, longer waits to avoid burning step budget and looking impatient.
  - Step budget should be higher for live human chat because most elapsed time is waiting, not acting.
  - If a representative refuses or a chat goes dead, the agent needs an explicit recovery pattern: ask the user for approval, end the chat, and start a fresh chat with the same task.
- Implemented follow-up:
  - Added Amex live-chat pacing guidance: 30-60s waits after agent join, 60-120s when the rep says they are reviewing/checking, and at most one short nudge after roughly 2 minutes of silence.
  - Added Hangup and Call-again recovery guidance with mandatory user confirmation before ending and restarting a chat.
  - Raised `scripts/start.py --max-steps` default from 30 to 50 for live runs.

### 2026-05-06 Architecture deepening
- Browser launch/profile/CDP policy now lives in `src/agent/browser_runtime.py`; `scripts/start.py` builds a `ChromeLaunchConfig`, and `ChatNavigator` consumes the same regular-Chrome guard instead of exporting private helpers.
- `AgentBrain` is now a coordinator. LLM creation/fallback, user input/tool registration, evidence capture/result extraction, and result types live in `llm_runtime.py`, `user_input.py`, `evidence.py`, and `result.py`.
- Amex and generic site adapters no longer carry long inline prompts; base scaffolds moved to `prompts/amex/base.txt` and `prompts/generic/base.txt`, rendered through `src/sites/prompt_renderer.py`.
- Verification: `ruff check src scripts tests` passed; `pytest tests -q -m "not slow"` passed with 69 tests; `scripts/start.py --dry-run ... --fallback-model gemini-flash` passed. Full slow browser tests were intentionally not run because they enter real browser/login paths.
- [x] First usability pass after successful rough E2E (2026-05-07) — shortened `scripts/start.py --help` to the common supervised path, added `--attach` as the friendly existing-tab alias, exposed live `AgentBrain.step_log` progress through `/tasks/{task_id}`, and rendered step progress in the React dashboard activity pane.
- [x] Dashboard supervised launch flow (2026-05-07) — added `/browser/launch` to open a visible FlyingPig Chrome from the API, added Launch/Attach browser controls in the React task form, and made task creation pass the prepared CDP URL so users can prep login/MFA before deploying the agent.
- [x] User-profile launch defaults (2026-05-07) — changed real-run Chrome default from a blank dedicated profile to the persistent copied default-profile path and kept browser-use attaching to the prepared Amex tab.
- [x] Side-panel pivot (2026-05-07) — made the Chrome extension side panel the preferred supervised surface, streamed daemon progress events over WebSocket, added `scripts/start.py --browser-only`, and stopped opening a dashboard tab by default.
- [x] Extension E2E harness (2026-05-07) — added a Puppeteer-managed mock side-panel smoke (`npm run test:extension`) that installs the unpacked extension, opens the mock Amex page, verifies WebSocket daemon progress, and keeps copied-profile Chrome plus Computer Use reserved for real-profile smoke tests.
- [x] Helper-sidepanel prototype archived on GitHub (2026-05-07) — initialized git, committed the reconnectable daemon + improved side panel, created private repo `lifan-builds/flyingpig`, and pushed `main`.
- [x] Pure-extension runtime rollback (2026-05-07) — rejected the all-in-extension implementation because it would give up browser-use's advanced browser/LLM loop; restored the extension as a UI/control plane for the local helper.
- [x] Add beta helper entrypoint (2026-05-07) — `flyingpig-helper` starts the WebSocket daemon and launches FlyingPig-controlled Chrome with the side panel's default CDP endpoint, replacing the two manual development commands for beta sessions.
- [x] Add macOS beta helper service path (2026-05-07) — `flyingpig-macos-helper install` writes a per-user LaunchAgent that starts the helper daemon at login; side panel now launches FlyingPig Chrome on demand through `/browser/launch`.
- [x] Build local beta release artifact (2026-05-07) — `scripts/build_beta_release.py --clean` creates `dist/flyingpig-beta-0.1.0.zip` with helper code, side-panel extension, prompts, README, and beta install guide.
- [x] Add model-owned Decision Checkpoints (2026-05-12) — structured human-in-the-loop choices for strategy pivots, offers, irreversible actions, verification, and timeout-risk moments; side panel renders option buttons, sends selected option id plus exact approved message, supports configurable user-attention alerts, and session artifacts save checkpoint audit events.
- [x] Harden Decision Checkpoints v2 (2026-05-12) — schema validation now rejects malformed model-generated checkpoints, irreversible actions require exact outbound messages, pending checkpoints survive side-panel reconnects as structured choices, and daemon results expose checkpoint event counts.
- [x] Live Oura supervised run and pacing fix (2026-05-12) — Oura specialist Levi applied 3 complimentary months to `xinyiw9596@gmail.com` with reference `#6847916`; added stronger patience/tone guidance plus stale `report_outcome` guard for pending confirmation/reference details.
- [x] Release-ready extension-first beta verification pass (2026-05-15) — mapped docs/beta.md gates to automated/manual evidence, strengthened the extension smoke for disabled Start, offline setup, launch/focus, cancel, and checkpoint reconnect, hardened helper LaunchAgent failure output, fixed helper stop to boot out the running service target, verified helper status/stop/start plus `/health`, and rebuilt `dist/flyingpig-beta-0.1.0.zip`.
- [x] Dashboard cockpit pivot (2026-05-17) — replaced the Chrome side-panel primary surface with a dashboard tab opened by the extension action, removed the `sidePanel` manifest dependency, made the work-window URL the only task target, and renamed the extension smoke/protocol tests around the dashboard.
- [x] Helper-first dashboard pivot (2026-05-19) — moved the cockpit assets to `dashboard/`, served them from the helper at `/dashboard/`, made `flyingpig-helper` open the localhost dashboard without launching the work window, and changed the deterministic Puppeteer smoke to use the helper-hosted UI instead of loading an unpacked extension.
- [x] Dashboard HUCA restart control (2026-05-20) — added a helper-owned `huca` command and dashboard button that cancels any active run, preserves the same task/work-window settings, and starts a fresh-chat browser-use run with explicit Hangup and Call-again instructions.
- [x] Native desktop shell v1 (2026-05-20) — added an Electron desktop shell that starts a development helper or packaged sidecar, chooses an available helper port, waits for `/health`, loads the helper-served `/dashboard/`, shows retry/diagnostics on helper startup failure, and stops the helper on normal app quit. Added PyInstaller/electron-builder packaging path plus desktop unit/smoke coverage. Packaged macOS app was built as a zip target, launched against the PyInstaller sidecar, verified through `/health`, helper logs, Chromium remote-debugging DOM inspection, and app-close helper shutdown.
- [x] Packaged helper browser-use prompt resources (2026-05-20) — fixed PyInstaller sidecar packaging to include `browser_use.agent.system_prompts` Markdown resources. Verified the packaged app against a local mock page with `max_steps=0`: browser-use initialized and returned `partial / No result captured` instead of failing with `No module named 'browser_use.agent.system_prompts'`.
- [x] Pine-informed protocol hardening (2026-05-21) — made the helper/dashboard run protocol explicit around structured user-attention/auth/result events, backend-owned wait states, pre-flight safety gates, evidence-linked results, and a task-first dashboard surface while preserving the supervised browser-first wedge.
- [x] Desktop-first product-path cleanup (2026-05-21) — made Electron the only normal user-facing entry point, archived the old Chrome extension and React frontend under `docs/legacy/`, kept helper/dashboard as internal runtime/UI details, and removed helper service/extension aliases from active docs/release.
- [x] Dashboard task-brief and work-window affordance cleanup (2026-05-21) — replaced the six task shortcut buttons with one editable brief starter selector, made the problem brief label explicit, added an Open Work Window action beside the offline status pill, and aligned smoke coverage/docs with the new label.
- [x] Run readiness and speed dashboard (2026-05-23) — added helper/runtime timing spans, evidence-linked timing summaries, guided readiness checklist, exact Start-disabled reasons, timing panel, reconnect-safe timing snapshots, and dashboard smoke benchmark output.
- [x] Prepare and package 1.0.0 release (2026-05-24) — bumped active version to 1.0.0, built source and macOS desktop zip artifacts, scanned release contents, and prepared `v1.0.0` for push.
- [ ] Run supervised Amex beta smoke from the dashboard with user login/MFA and send confirmation.
- [x] Extend dashboard smoke coverage or document full mock-agent blocker (2026-05-15) — dashboard mock-daemon smoke now covers the release UX states; full dashboard-driven browser-use mock-agent run remains documented in docs/beta.md as blocked on deterministic LLM/CDP work-window orchestration.

### 2026-05-12 Oura supervised run and pacing findings
- Live Oura result: specialist Levi confirmed 3 complimentary membership months were applied to `xinyiw9596@gmail.com`; reference number `#6847916`.
- First continuation failure: Flying Pig finalized while Levi had said he was still checking. It needed to continue waiting in the existing live chat.
- Second continuation failure: Flying Pig again reported no reference/timing while Levi had said "allow me one moment please"; Computer Use saw the reference arrive immediately after.
- Implemented follow-up: runtime policy now treats rep "checking/reviewing/one moment" messages as Active Human Work, asks for 60-90s patience, and encourages warmer appreciative follow-ups.
- Implemented follow-up: `report_outcome` now re-inspects visible page text and blocks stale "no reference provided" finalization when pending human-work phrases or new reference numbers are visible.
- Validation after fixes: `pytest tests/integration tests/unit` passed; `pytest tests/e2e/test_amex_e2e.py -x -vv` passed; full `pytest tests/` was attempted but browser e2e cleanup wedged after a transient mark, so the hung process was stopped.

### 2026-05-15 Extension-first beta release evidence
- Verification passed: `ruff check src scripts tests`; `pytest tests -q -m "not slow"` (116 passed, 2 deselected); elevated `npm run test:extension`; `python scripts/build_beta_release.py --clean`; `git diff --check`.
- Beta artifact: `dist/flyingpig-beta-0.1.0.zip` rebuilt after helper stop fix, docs/install-guide fixes, and release privacy fixes. SHA-256: `4f70066a332f23a2a3b4db1d21e1fd5fd4d49cef3718e4538c45de1a603f380d`.
- Helper service flow verified: status showed `state = running`, `/health` returned `{"ok":true,"sites":["amex","generic","oura"]}`, stop made status report not running and `/health` unavailable, start restored running state and `/health`.
- Release-blocking helper UX fix: stale/not-loaded LaunchAgent failures now print a recovery-focused launchctl message instead of a Python traceback.
- Release-blocking helper stop fix: `flyingpig-macos-helper stop` now boots out `gui/<uid>/com.flyingpig.helper` and fails loudly if launchctl refuses instead of printing success while the service keeps running.
- Release privacy scan fix: removed the hardcoded API auth JWT secret from `src/api/auth.py`, added `api_secret_key` environment configuration, removed the local editable path from `requirements.txt`, and added an explicit beta gate forbidding PII/API keys/credentials/tokens/cookies/logs/recordings/user-specific account info in release artifacts.
- Dashboard smoke now covers setup/offline state, disabled Start before Work Window Connected, dedicated work-window launch, active-run cancel, checkpoint restore after dashboard reload, and checkpoint answer submission.
- Remaining manual blocker: supervised Amex beta smoke still needs a tester present for Amex login/MFA and explicit send confirmation from the dashboard. Exact smoke path and blocker taxonomy are recorded in docs/beta.md.

### 2026-05-19 Helper-first dashboard and external chat-surface smoke
- Helper-first refactor verification: `ruff check src scripts tests`; `pytest tests -q -m "not slow"` (122 passed, 2 deselected); elevated `npm run test:dashboard`; `python scripts/build_beta_release.py --clean`; zip content check confirmed `dashboard/` is included and `extension/` is absent; `zipgrep` privacy scan found no common secret/PII/log/recording patterns; `git diff --check` passed.
- Public chat-surface checks used headless Puppeteer to load sites, open chat widgets, and type harmless draft text without pressing Enter or submitting. Clean widget/input passes: LiveChat (`https://www.livechat.com/`) and Olark (`https://www.olark.com/`). Screenshots: `/private/tmp/flyingpig-livechat-chat-check.png`, `/private/tmp/flyingpig-olark-targeted-chat-check.png`.
- Compatibility observations: several public sites exposed support/product links that generic text matching could confuse for chat launchers (Solved, HelpCrunch, Chaport, JivoChat, Drift/Freshworks, ProProfs, Smartsupp, REVE Chat, Chatra). This reinforces that the browser-use visual/model loop should own chat-surface selection, not a deterministic text-only rule.
- Live LLM-driven external-site agent runs were blocked in this environment: Anthropic/OpenAI/Gemini/Cliproxy API keys were not set and `http://127.0.0.1:8317/v1/models` was unavailable. The external pass therefore verified dashboard/work-window/browser chat-surface mechanics, not a submitted customer-service conversation.
- Follow-up correction: CLIProxyAPI was already running on `127.0.0.1:8317`; elevated model check succeeded with the configured local key. A real browser-use mock Amex run with `model=cliproxyapi` and `gpt-5.5` completed successfully: cancellation request sent, `$50` retention credit accepted, confirmation `MOCK-12345` captured, and session saved to `recordings/mock_run/session_american_express_20260519_191928.json`.
- Helper lifecycle updated to be CLI-owned: `flyingpig-helper` opens the dashboard and waits in the foreground; users stop it with Ctrl+C. The dashboard does not own helper shutdown.

### 2026-05-20 Dashboard HUCA restart control
- Added first-class `huca` support to the helper WebSocket and REST run APIs. The helper now stores the current run request, cancels the active agent run when needed, and restarts against the same site, task, CDP endpoint, and target URL.
- HUCA restarts prepend an explicit recovery preamble telling browser-use to end/leave a refused or dead chat, start a fresh chat in the same browser session, treat prior scrollback as read-only background, and restate the original task from scratch.
- Dashboard UX now exposes a `HUCA` button beside Start/Cancel. It is enabled when the helper, work window, and task brief are available, including during an active run.
- Verification: `ruff check src scripts tests`; `pytest tests -q -m "not slow"` (124 passed, 2 deselected); elevated `npm run test:dashboard`; focused daemon tests (`pytest tests/unit/test_daemon_server.py tests/unit/test_daemon_run_session.py -q`) passed.

### 2026-05-21 Pine-informed protocol hardening
- Dashboard now starts from the customer-service chore: task brief question, common shortcuts (lower bill, cancel subscription, dispute fee, refund/courtesy credit, escalate to human, continue chat), success criteria, and visible permission boundaries before the browser mechanics.
- Helper run state now uses explicit statuses: `preparing`, `ready_to_start`, `running`, `waiting_on_user`, `waiting_on_rep`, `waiting_on_login`, `waiting_on_auth`, `checkpoint_pending`, `recovery_pending`, `completed`, `failed`, and `cancelled`.
- User-attention protocol now normalizes pending requests into structured events for decision checkpoints, missing information, OTP/MFA, manual login, auth, account-blocked, resume-after-auth, attachments, irreversible actions, offers, and recovery. Pending structured events remain in the reconnect snapshot.
- Added helper-side pre-flight validation before starting a run: task/site presence, supervised-browser permission, user authorization, work-window/target URL, evidence capture, login expectation, unsupported phone/email/credential scope, and checkpoint requirement for irreversible actions.
- Active Human Work progress phrases now surface as `waiting_on_rep` plus an `active_human_work` event so the dashboard shows representative review/wait states distinctly from generic running.
- Final results now broadcast `result_ready` with outcome summary, evidence/transcript reference counts, human reached, offer/result, unresolved items, time-saved field when available, and checkpoint decisions.
- Tests added/updated for reconnect-safe structured attention, pre-flight failures, waiting-on-rep snapshots, manual-login snapshots, evidence-linked result payloads, and dashboard protocol helpers.
- Verification: `ruff check src scripts tests`; `pytest tests/unit/test_daemon_run_session.py tests/unit/test_daemon_server.py -q` (21 passed); elevated `npm run test:dashboard`; `pytest tests -q -m "not slow"` (130 passed, 2 deselected); `git diff --check`.
- Remaining: supervised real Amex beta smoke still needs a tester present for login/MFA and explicit send/approval moments.

### 2026-05-21 Architecture deepening follow-up
- Extracted Active Human Work phrase/result-guard semantics into `src/agent/human_work.py` so daemon progress classification and `report_outcome` stale-result prevention share one module.
- Extracted helper-owned run-start policy into `src/daemon/preflight.py`; REST/WebSocket start paths now use the same Pre-flight Safety Gate instead of keeping policy inside transport code.
- Added `src/agent/run_orchestration.py` as the Agent Run Plan seam between daemon transport and `AgentBrain`; HUCA recovery instructions moved to `prompts/generic/huca_recovery.txt`.
- Moved result-ready payload shaping into Evidence Bundle code (`src/agent/evidence.py`) and kept `src/daemon/run_session.py` as a compatibility publisher over that shape.
- Deepened Controlled Chrome profile handling with domain profile modes and exposed the advanced user default profile option in the dashboard/helper paths while preserving the explicit Chrome default-profile guard.
- Centralized Support Profile validation and prompt-context rendering in `src/sites/profiles.py`; profile-backed adapters now consume the rendered context.
- Shifted dashboard pending-request status/progress decoding into `dashboard/dashboard_protocol.js` with protocol smoke coverage.
- Verification: `ruff check src scripts tests`; focused module tests (`pytest tests/unit/test_human_work.py tests/unit/test_run_orchestration.py tests/unit/test_daemon_run_session.py tests/unit/test_daemon_server.py tests/unit/test_browser_runtime.py tests/unit/test_registry.py -q`, 53 passed); `pytest tests -q -m "not slow"` (137 passed, 2 deselected); `node scripts/test_dashboard_protocol.mjs`; elevated `npm run test:dashboard`; `git diff --check`.

### 2026-05-21 Desktop-first product-path cleanup
- Accepted ADR-0005: the Electron desktop app is the only normal user-facing product path. The Python helper remains a sidecar/runtime, and the helper-served dashboard remains the cockpit UI loaded inside the app.
- Archived the old Chrome extension and old React frontend under `docs/legacy/` so they are reference code only, not active product surfaces.
- Removed the `test:extension` package alias and removed `flyingpig-macos-helper` from console scripts. The LaunchAgent helper service source remains only as legacy/dev reference and is excluded from the beta zip.
- Changed direct `flyingpig-helper` behavior so it no longer opens a browser dashboard by default; `--open-dashboard` is now the explicit developer convenience flag.
- Updated README, beta docs, setup UI, CONTEXT, release install text, and ADR-0003 supersession language around the single app path.
- Verification: `ruff check src scripts tests`; `pytest tests/unit/test_helper_service.py tests/unit/test_daemon_server.py tests/unit/test_browser_runtime.py -q` (33 passed); elevated `npm run test:desktop`; elevated `npm run test:dashboard`; `pytest tests -q -m "not slow"` (137 passed, 2 deselected); `python scripts/build_beta_release.py --clean`; release zip content check found no `extension`, `frontend`, `docs/legacy`, `helper_service`, or `macos_helper` entries; `git diff --check`.

### 2026-05-23 Run readiness and speed dashboard
- Added a PII-free `Run Timing Span` path: launch, pre-flight, AgentBrain construction, work-window attach, first observation, browser-use step, model planning step, user wait, representative wait, and result capture spans can flow through WebSocket/REST state and final `result_ready` payloads.
- Final results now include inline `timing_spans` and `timing_summary` data linked to the Evidence Bundle payload, while timing metadata stays phase/duration/status-only.
- Dashboard first viewport now includes a readiness checklist for Helper, Work Window, Chat Surface, Task Brief, Login/Auth, and Safety Gate plus an exact Start-disabled reason beside Start.
- Dashboard renders timing spans in a Run Speed panel and in result details; the mock dashboard smoke now checks readiness transitions, disabled Start copy, timing/progress rendering, reconnect behavior, narrow-width layout, and benchmark output.
- Verification: `pytest tests/unit/test_daemon_run_session.py tests/unit/test_daemon_server.py -q` (22 passed); `node scripts/test_dashboard_protocol.mjs`; elevated `npm run test:dashboard` with benchmark output (`helper_online=2264ms`, `work_window_ready=2341ms`, `mock_run_done=2483ms`); `ruff check src scripts tests`; `git diff --check`.

### 2026-05-24 Release 1.0.0 preparation
- Bumped active Python/Node release version from `0.1.0` to `1.0.0`; `scripts/build_beta_release.py` now defaults to `1.0.0`.
- Built source release bundle `dist/flyingpig-beta-1.0.0.zip` with SHA-256 `60646a86dd915b8c1bf0488e0201f2fa3e5b5e890e21cbe470936b82524784bb`.
- Built packaged helper sidecar `dist/helper/flyingpig-helper` and desktop artifact `dist/desktop/Flying Pig-1.0.0-arm64-mac.zip` with SHA-256 `dd949fd8c4f92616e0ad07fcec59c3274fbd80899556e909078cfc1d993a623a`; desktop package is unsigned because no local Developer ID identity is configured.
- Release scans found no common secret/private-key patterns, emails, `.env`, cookies, logs, recordings, databases, or legacy `extension/` and `frontend/` paths in the 1.0.0 source bundle or desktop zip.
- Verification: `ruff check src scripts tests`; `pytest tests -q -m "not slow"` (137 passed, 2 deselected); elevated `npm run test:dashboard`; elevated `npm run test:desktop`; `python scripts/build_beta_release.py`; `npm run build:helper`; `npm run desktop:package`.

### 2026-05-24 Release 1.0.1 publishing pass
- Kept the already-pushed `v1.0.0` tag intact and prepared `1.0.1` for the publishable GitHub Release so the tag, code, and downloadable artifacts match.
- Added the refreshed light dashboard screenshots and Chinese release note under `docs/releases/v1.0.1-zh.md`; source release bundles now include release notes and screenshot assets.
- Included the final task-intake and model-settings UI changes: primary flow defaults to automatic agent approach selection, manual approach is under Advanced, and model provider keys can be saved to the user-local env file without exposing saved values.
- Built source release bundle `dist/flyingpig-beta-1.0.1.zip` with SHA-256 `5f9e2cfc48933892513746ce04fc4e249a03ca8acb20811d8d41cb41a779c60b`.
- Built packaged helper sidecar `dist/helper/flyingpig-helper` and desktop artifact `dist/desktop/Flying Pig-1.0.1-arm64-mac.zip` with SHA-256 `fef65229976165d5665782510a049a8ca44dc78a6d5eaafbe2bc0ed8f6159c48`; desktop package remains unsigned because no local Developer ID identity is configured.
- Release scans found no common secret/private-key patterns, emails, `.env`, cookies, logs, recordings, databases, or legacy `extension/` and `frontend/` paths in the 1.0.1 source bundle or desktop zip.
- Verification: `ruff check src scripts tests`; `pytest tests -q -m "not slow"` (138 passed, 2 deselected); elevated `npm run test:dashboard` (`helper_online=1828ms`, `work_window_ready=2052ms`, `mock_run_done=2199ms`); elevated `npm run test:desktop`; `python scripts/build_beta_release.py`; `npm run build:helper`; `npm run desktop:package`; `git diff --check`.

### 2026-05-25 Local scorecards and desktop update foundation
- Added a PII-free Run Scorecard to final result payloads. Scorecards include final status, site/profile, goal type, human reached, HUCA attempts, checkpoint count, user-intervention count, duration/timing, offer/result, blocked reason, unresolved item count, and user-confirmed outcome.
- The daemon now enriches final results with run metadata and HUCA attempt count, and exposes `/run/outcome` so the current scorecard can be marked solved, partial, or failed.
- Dashboard result UI now shows scorecard status, HUCA attempts, outcome marking buttons, and local beta stats derived from localStorage scorecards rather than transcripts or chat logs.
- Added `electron-updater` foundation for GitHub-backed desktop updates: packaged-only checks, menu entries for checking/installing updates, preload IPC hooks, GitHub publish config, hyphenated artifact names, and `docs/desktop-auto-update.md`.
- Packaging now emits `dist/desktop/latest-mac.yml` and matching `Flying-Pig-1.0.1-arm64-mac.zip` artifacts. The app remains unsigned, so auto-update is not yet production-reliable for normal Mac users.
- Verification: `ruff check src scripts tests`; `pytest tests -q -m "not slow"` (139 passed, 2 deselected); `pytest tests/unit/test_daemon_run_session.py tests/unit/test_daemon_server.py -q` (23 passed); `node scripts/test_dashboard_protocol.mjs`; elevated `npm run test:dashboard` (`helper_online=2044ms`, `work_window_ready=2283ms`, `mock_run_done=2430ms`); elevated `npm run test:desktop`; `npm run desktop:package`; `git diff --check`.

### 2026-05-25 Auto-update release hardening
- Confirmed the `lifan-builds/flyingpig` GitHub repository is public, so installed apps can read release assets without embedding a token.
- Confirmed the published `v1.0.1` release is not an update-capable baseline: it lacks `latest-mac.yml`, lacks the hyphenated updater zip asset name, and predates the updater-enabled app code.
- Added macOS hardened-runtime signing/notarization config, Electron entitlements, and a GitHub Actions `Desktop Release` workflow that requires Developer ID and App Store Connect secrets before publishing update artifacts.
- Added `scripts/verify_desktop_update_release.mjs` and `npm run desktop:verify-update` to verify `latest-mac.yml`, zip size, zip sha512, code signing/Gatekeeper when required, public repo visibility, and GitHub release update assets.
- Bumped active release version to `1.0.2` across Node/Python package metadata, source bundle default, and legacy API health version. `v1.0.2` should be the first signed update-capable baseline.
- Local package verification produced `dist/desktop/latest-mac.yml` and `Flying-Pig-1.0.2-arm64-mac.zip`; unsigned local builds pass metadata verification but fail `--require-signed`, as intended on this machine with no Developer ID identity.
- Verification: `ruff check src scripts tests`; `pytest tests -q -m "not slow"` (139 passed, 2 deselected); `node --test desktop/auto_update.test.mjs`; `node scripts/test_dashboard_protocol.mjs`; elevated `npm run test:desktop`; elevated `npm run test:dashboard` (`helper_online=2286ms`, `work_window_ready=2509ms`, `mock_run_done=2657ms`); `npm run desktop:package`; `npm run desktop:verify-update`; `npm run desktop:verify-update -- --require-signed` failed as expected due to missing local Developer ID identity; `npm run desktop:verify-update -- --github --tag=v1.0.1` failed as expected because the old release lacks updater assets.
