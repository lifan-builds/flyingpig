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

## Archive
(Empty — initial migration.)
