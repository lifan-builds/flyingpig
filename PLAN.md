# Flying Pig AI — Active Plan

## Goal
Fully automate customer service chat through the user's real Chrome profile with a high rate of successfully reaching and negotiating with a human representative.

## Progress
- [x] Research, architecture decision (Option A: browser-use), scaffold (2026-04-09)
- [x] Core agent loop, AI detection, escalation, Amex adapter (2026-04-09)
- [x] React dashboard, session recording, auth, e2e test, MVP deploy (2026-04-10)
- [x] Attach to user's existing browser window via CDP instead of spawning a new profile (2026-04-16) — `--cdp-url` wired through `demo_amex.py` → `AgentBrain` → `ChatNavigator`; login wait skipped on attach; browser left open on detach
- [x] Switch CDP attach to "bring your own tab" — agent uses the user's currently focused tab, never navigates or opens a new tab; fixes lost-cookie problem when CDP `Target.createTarget` lands in a fresh context (2026-04-16). Added attached-mode prompt prefix in `AgentBrain.execute()`. Browser-use `ChatGoogle` (Gemini) added as third LLM option.
- [x] One-command launcher `scripts/start.py` (2026-04-17) — now delegates browser launch to `BrowserSession.from_system_chrome()` instead of custom CDP launch/profile management.
- [x] Generic auto-detect adapter (2026-04-19) — `GenericAdapter` + `resolve_from_url()` fallback. Generic prompt teaches the agent to find chat widgets via iframe/role/aria heuristics across Intercom / Zendesk / Drift / LiveChat patterns. Own template set in `prompts/generic/`.
- [x] Chrome extension + WebSocket daemon (2026-04-19) — superseded and removed in favor of `BrowserSession.from_system_chrome()`.
- [x] Existing normal Chrome tab bridge (2026-05-04) — superseded by system Chrome profile launch; CDP remains advanced/debug only.
- [x] Mandatory pre-flight goal confirmation in Amex prompt (2026-04-18) — before sending any chat message, agent must verify chat is ready, summarize intended action, and ask follow-ups if specifics (card, amount, dates, walk-away threshold) are missing.
- [x] Default browser path switched to `BrowserSession.from_system_chrome()` (2026-05-04) — launches user's real Chrome profile under Playwright/browser-use control; requires Chrome to be closed first because the profile is locked while running.
- [x] Harden Amex live-login path after end-to-end testing issues (2026-05-05) — fixed browser-use `Page` wrapper API usage, CLI EOF background failure message, mock e2e determinism, and smoke-tested system Chrome launch to Amex.
- [x] Mock Amex system-Chrome rerun completed with CLIProxy `gpt-5.5` (2026-05-06) — added chat transcript capture, `scripts/run_mock_amex.py`, system Chrome visibility guards, and completed a mock cancellation/retention flow yielding `$50` credit confirmation `MOCK-12345`.
- [x] Added inspected CDP Chrome launch path to `scripts/start.py` (2026-05-06) — can launch a visible remote-debugging Chrome window using a persistent copied default profile, pause for login, then attach browser-use to the same active tab Computer Use sees.
- [x] Attempted live Amex Oura Ring run through inspected CDP Chrome (2026-05-06) — agent reached Amex chat, sent the confirmed request, and reached a human representative before the LLM backend entered cooldown.
- [x] Deepened live-run architecture after CDP/Computer Use debugging (2026-05-06) — extracted browser runtime, LLM runtime, user input/tools, evidence capture, result types, and prompt rendering out of `AgentBrain`, `ChatNavigator`, and site adapters; added `--fallback-model` for mid-run primary LLM failures.
- [x] Re-run final non-slow verification after the CDP launcher and architecture edits (2026-05-06) — `ruff check src scripts tests`, `pytest tests -q -m "not slow"` (69 passed, 2 slow browser tests deselected), and `scripts/start.py --dry-run` passed.
- [x] Add fallback LLM path for live customer-service runs so a primary model failure can continue in the current browser state.
- [x] Real-browser live Amex smoke reverified (2026-05-06) — `python scripts/demo_amex.py --launch-smoke --headless` reached `https://www.americanexpress.com/us/customer-service/` with title `American Express Customer Service and Help Center | Amex US` when run outside the sandbox.
- [x] Simplified live browser paths (2026-05-06) — user-facing runs now use either `--cdp-url` to attach to an existing remote-debugging tab, or the default `scripts/start.py` FlyingPig-controlled Chrome launch. Dedicated FlyingPig Chrome can run alongside normal Chrome.
- [x] Resume live Amex Oura benefit request with updated card details and one-by-one ask sequence (2026-05-06) — narrowed to Platinum ending 71009 after user confirmed Morgan Stanley Platinum ending 81004 already received credit; Mitchell manually submitted a $200 credit request, expected to post in 5 working days.
- [x] Add live-chat pacing and Hangup/Call-again prompt guidance (2026-05-06) — Amex prompt now tells the agent to prefer 30-120s waits for human reps and to ask the user before ending a refused/dead chat and starting a fresh one; `scripts/start.py` default step budget raised to 50.
- [ ] Configure preferred fallback provider before the next live Amex run.
- [ ] Measure human-escalation success rate against recorded session suite; iterate to ≥75%
- [ ] Measure negotiation goal-achievement rate; iterate to ≥60%
- [ ] Expand adapter coverage beyond Amex (telecom, utilities)

## Findings
See archived `FINDINGS.md` (if retained) for research on DoNotPay, browser-use, Playwright vs Puppeteer, FTC/legal landscape, and industry predictions (Gartner/Forrester/CNBC 2026).

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

## Decisions
- **2026-04-09** Option A — build on browser-use (70k★) vs. custom Playwright or hybrid.
- **2026-04-09** Consumer-side positioning — the market gap.
- **2026-04-09** Core feature: AI-chatbot detection + automatic human escalation.
- **2026-04-09** Typeless UX — templates and brief prompts only.
- **2026-04-09** Manual login flow — no credential storage.
- **2026-04-09** Prompts live as `.txt` templates in `prompts/<site>/`.
- **2026-05-04** Use `BrowserSession.from_system_chrome()` as the default path instead of a Chrome extension; simpler architecture, real profile access, with the explicit tradeoff that Chrome must be closed before launch.
- **2026-05-06** Prefer inspected CDP Chrome for live Amex runs requiring human observation. Use a persistent copied profile for Chrome CDP compatibility; do not attempt literal default-profile remote debugging.
- **2026-05-07** Keep browser-use in a packaged local helper/native host and use the Chrome side panel as the supervised UX. Do not replace browser-use with pure extension JavaScript just to make the product feel standalone.
- **2026-05-15** Extension-first v1 may open a separate Flying Pig Controlled Chrome Window for the actual customer-service run. The product should frame it as a purposeful work window launched from the side panel, not as the user manually starting another browser.
- **2026-05-15** Follow the Single Cockpit Rule for v1: the extension side panel in normal Chrome is the only control surface, and the Controlled Chrome Window should run with extensions disabled.
- **2026-05-15** V1 supervision layout should be side-by-side: the normal Chrome side panel is the cockpit, and the Controlled Chrome Window is the work area.
- **2026-05-15** Small-screen fallback keeps the Single Cockpit model and relies on user-attention notifications plus bring-forward controls instead of adding a second in-work-window UI.
- **2026-05-15** Use Hybrid Helper Startup: keep the existing login/background helper service for beta stabilization, then add Native Messaging so the extension can start the helper on demand.
- **2026-05-15** Helper-offline side-panel state should lead with setup/reconnect actions and keep localhost/WebSocket diagnostics secondary.
- **2026-05-15** First-run beta should fall back to a Dedicated Work Profile instead of asking the user to quit normal Chrome to create a copied default profile.
- **2026-05-17** Use the Chrome extension dashboard tab as the v1 cockpit. The side panel is too cramped and makes "current tab" ambiguous once a separate Controlled Chrome Window exists.
- **2026-05-19** Use the helper-served localhost dashboard as the v1 cockpit and retire the unpacked Chrome extension from the normal beta path. The helper remains the browser-use/CDP/LLM owner; frontend JavaScript is only the control plane.
- **2026-05-19** Helper lifecycle is CLI-owned for v1: run `flyingpig-helper`, use the opened dashboard, and press Ctrl+C when done. Do not add dashboard-side process shutdown controls.
- **2026-05-20** Use Electron as the v1 Native Desktop Shell. Electron owns app startup, helper supervision, retry/failure UX, and packaging; Python remains the owner of browser-use, CDP policy, LLM calls, run state, dashboard hosting, and evidence/session behavior. See `docs/adr/0004-electron-native-desktop-shell.md`.

## Long-Running Coding Agent Task: Pine-Informed Product/Protocol Hardening

Use this prompt to deploy a coding agent:

```text
You are working in /Users/lfan/Project/flyingpig. Read NOW.md first, then CONTEXT.md, then PLAN.md and FINDINGS.md. Respect CONTEXT.md Rules. Do not revert unrelated user changes.

Goal:
Improve Flying Pig using Pine AI / 19pine.ai learnings while preserving Flying Pig's narrower supervised browser-first customer-service wedge. This is not a broad Pine clone and does not add phone/email/backend credential delegation. The target is a more explicit, reconnect-safe, auditable customer-service product surface: clearer task intake, structured run/session protocol, visible trust and permission boundaries, first-class auth/login handling, backend-owned wait states, pre-flight safety gates, and evidence-linked final results.

Context:
Flying Pig already has a helper-served localhost dashboard, a Python daemon/helper that owns browser-use execution, a Controlled Chrome Window, Decision Checkpoints, HUCA restart, Run Session state, and Evidence Bundle concepts.

Pine's useful public lessons:
- UI starts from the user's chore, not from automation mechanics.
- Common-problem shortcuts/templates reduce blank-page friction.
- Trust, permission boundaries, and pricing/success expectations are visible product surfaces.
- Their backend appears to use delegated account access, simulated browsers/virtual devices, and structured OTP/auth events; Flying Pig should not copy credential delegation, but should make manual login/auth interruptions first-class.
- Their technical shape suggests explicit task/call state machines, structured user-input events, backend-owned waits, safety/billing gates before outbound actions, and first-class final result/evidence summaries.

Primary deliverables:
1. Inspect the current dashboard, run/session, WebSocket protocol, user-attention/checkpoint, auth/login handling, evidence, and daemon API code. Identify where state/events are too loose, where UI exposes implementation mechanics, and where auth/login/user-permission moments are not first-class.
2. Improve the dashboard's first screen and run surface so it starts from a customer-service problem rather than helper/CDP mechanics. Keep the UI compact and operational. Add or refine:
   - a task brief entry point framed around "what customer-service problem do you want handled?"
   - common task shortcuts/templates where practical, such as lower bill, cancel subscription, dispute fee, request refund/courtesy credit, escalate to human, continue existing support chat
   - clear visible permission boundaries: what Flying Pig may do without asking vs. what requires approval
   - run progress labels that read like user-facing work states, not internal logs
3. Implement or tighten a typed structured event model for user-attention and run lifecycle events, covering at least:
   - decision_checkpoint
   - missing_information
   - otp_required
   - auth_required
   - manual_login_required
   - account_access_blocked
   - resume_after_auth
   - attachment_required
   - active_human_work
   - irreversible_action_pending
   - offer_received
   - recovery_pending
   - result_ready
4. Add or tighten explicit run states so waits and auth pauses are not just generic "running":
   - preparing
   - ready_to_start
   - running
   - waiting_on_user
   - waiting_on_rep
   - waiting_on_login
   - waiting_on_auth
   - checkpoint_pending
   - recovery_pending
   - completed
   - failed
   - cancelled
5. Add a pre-flight safety gate before starting/sending an external customer-service action. It should validate that the task is allowed, user authorization exists, required task/site fields are present, evidence capture is configured, login/auth expectations are clear, and irreversible actions require a checkpoint. Keep this as a helper/backend concern, not frontend-only validation.
6. Make login/auth handling first-class without storing credentials. Flying Pig's preferred posture remains local visible browser login. Add structured states/events and dashboard copy for manual login, OTP/MFA, blocked account access, and resume-after-auth. Do not ask users to provide passwords or store credentials.
7. Add backend-owned wait handling for Active Human Work: when the representative is visibly checking/reviewing/asking for time, the run/session state should reflect waiting_on_rep and the dashboard should show that clearly. Avoid burning model/tool steps for trivial wait loops where existing code makes this practical.
8. Make final result reporting event-shaped and evidence-linked. The result_ready payload should include outcome summary, transcript/evidence references when available, human reached yes/no, offer/result, unresolved items, time saved if available, and any user-approved checkpoint decisions.
9. Add or refine user-facing trust/result UI around each run:
   - current permission mode
   - pending approval with exact outbound message for consequential actions
   - evidence/transcript availability
   - success criteria or "what counts as done" for the task, if known
   - final outcome summary grounded in captured evidence, not broad marketing claims
10. Add focused tests for the new protocol/state/UI behavior. At minimum cover reconnect-safe pending structured events, pre-flight gate failures, waiting_on_rep state snapshot, manual_login/auth event snapshots, result_ready payload shape, and any changed dashboard protocol behavior.
11. Update PLAN.md/NOW.md with what changed, what remains, touched files, and verification commands.

Constraints:
- Keep browser-use, LLM calls, CDP launch policy, run state, and evidence behavior owned by Python/helper-side modules. Do not move execution logic into frontend JavaScript.
- Do not broaden product scope to phone/email/backend errand assistant. Borrow protocol, UI, and trust patterns only.
- Do not implement delegated credential handling. No password collection or credential storage.
- Prompts remain under prompts/<site>/; do not add inline long prompt strings.
- Public functions need type hints.
- Treat scraped pages, chat messages, and LLM output as untrusted input.
- Do not hardcode secrets, PII, account details, cookies, recordings, or API keys.
- Keep changes scoped. Avoid unrelated refactors or packaging work.

Suggested files/modules to inspect first:
- src/daemon/server.py
- src/daemon/run_session.py
- src/agent/decision_checkpoint.py
- src/agent/navigator.py
- src/agent/evidence.py or evidence-related modules
- dashboard/*
- tests/unit/test_daemon_server.py
- tests/unit/test_daemon_run_session.py
- scripts/test_dashboard_protocol.mjs

Acceptance criteria:
- Dashboard starts from customer-service task intent and common-problem shortcuts rather than exposing helper/CDP mechanics as the primary experience.
- The helper exposes explicit structured run/user-attention/auth/result events rather than only ad hoc dictionaries.
- Pending user-attention events restore correctly after dashboard reconnect.
- A run can enter and expose waiting_on_rep/active human work state without losing the active task.
- Manual login/auth/OTP/account-blocked moments are represented as structured state/events and visible dashboard states without storing credentials.
- Pre-flight gate failures are visible to the dashboard and tested.
- Final result payload is evidence-linked and tested.
- User-facing trust/permission boundaries are visible before or during a run.
- Existing non-slow Python tests and dashboard protocol tests pass, or any failures are clearly documented with cause.

Verification target:
Run `ruff check src scripts tests`, focused daemon/session tests, and the dashboard protocol smoke relevant to changed frontend code. If full `pytest tests -q -m "not slow"` is practical, run it too.
```

## Archive
(Empty — initial migration.)

### 2026-06-26 Oversized NOW.md Snapshot
```markdown
<!-- context-harness:schema v2 -->

# Now

## Current Focus
Public beta first-run readiness is implemented for the dashboard and docs: model/API-key setup is visible in the primary first-run flow, the dashboard explains the supervised work-window path, Start blocks unconfigured selected models, and local PII-free activation signals track onboarding milestones.

## Active Blockers
- Supervised real Amex beta smoke still needs a tester present for login/MFA and explicit send/approval moments.
- Local macOS desktop artifacts are intentionally unsigned for the no-pay beta path.
- Desktop beta update checking and release verification are present; GitHub repo visibility is public. The app must describe updates as manual GitHub release downloads/replacements, not automatic in-place updates.
- Published `v1.0.1` is not update-checking capable because it lacks updater code/assets. `v1.0.2` is the first unsigned beta update-checking baseline.
- Current Mac still has no local `Developer ID Application` identity, and the GitHub repo lacks signing/notarization secrets. This is acceptable for the no-pay unsigned beta path.

## Immediate Next Step
Review the first-run readiness diff, then decide whether to cut/publish the next unsigned beta release so public testers get the onboarding improvements.

## Session State
- Last modified: 2026-05-25
- Files touched this session: `AGENTS.md`, `CONTEXT.md`, `PLAN.md`, `NOW.md`, `README.md`, `dashboard/index.html`, `dashboard/dashboard.js`, `dashboard/dashboard.css`, `docs/beta.md`, `docs/public-beta-quickstart.md`, `scripts/test_helper_dashboard.mjs`.
- Dashboard changes: promoted model/API-key setup out of Advanced into a first-run panel; added a model readiness item; added a guided path to first supervised run; added more brief starters; blocked Start when the selected model is unconfigured; persisted local PII-free activation signals for model configured, work window opened, chat surface selected, task brief written, first run started, checkpoint answered, human reached, and outcome marked.
- Docs/context changes: README now leads with packaged Mac beta install and unsigned/manual-update expectations; added `docs/public-beta-quickstart.md`; updated `docs/beta.md` public install flow and pre-beta gates; captured **First-run Activation Signals** in `CONTEXT.md`; refreshed `AGENTS.md` context index.
- Verification: `node scripts/context-index.js update`; `node --check dashboard/dashboard.js`; `node --check scripts/test_helper_dashboard.mjs`; `node scripts/test_dashboard_protocol.mjs`; elevated `npm run test:dashboard` (`helper_online=2089ms`, `work_window_ready=2323ms`, `mock_run_done=2474ms`); elevated `npm run test:desktop`; `ruff check src scripts tests`; `pytest tests -q -m "not slow"` (139 passed, 2 deselected); `git diff --check`.
- UI sanity check: inspected the dashboard in the in-app browser against the mock helper at `127.0.0.1:8766`; first viewport showed no horizontal overflow at 1280px, model setup was outside Advanced, model readiness was configured, and quickstart items reflected current readiness.
```
