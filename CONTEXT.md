# Context
<!-- context-harness:schema v3 -->

## Project
**Flying Pig AI** (客服上树) — consumer-side AI agent that drives customer service chat interfaces on behalf of users (bill negotiation, disputes, cancellations, retention). Python 3.12+ helper runtime, Electron desktop shell, helper-served dashboard, browser-use + Playwright for automation, and Gemini / Claude / OpenAI / CLIProxy OpenAI-compatible LLM options via `browser_use.llm` wrappers. Product direction: one user-facing desktop app; the Python helper and dashboard are internal runtime/UI implementation details. The helper owns browser-use execution, dashboard static hosting, run/session protocol, and Controlled Chrome Window launch. Current Chrome blocks CDP on the literal default profile, so use a copied or non-default profile for debug launches. Tooling: Ruff, Pytest, Puppeteer dashboard smoke tests, Electron desktop smoke tests.

## Structure
```
.
├── config/
├── dashboard/          # Helper-served cockpit UI that talks to local helper over WS
├── desktop/            # Electron desktop shell and helper supervision
├── docs/legacy/        # Archived old extension and React frontend references
├── prompts/            # LLM prompt templates by site
│   ├── amex/
│   └── generic/        # Site-agnostic fallback templates
├── scripts/            # start.py/daemon.py debug paths, release and smoke tooling
├── src/
│   ├── agent/          # Core loop: brain, navigator, browser_runtime, evidence, llm_runtime, user_input
│   ├── api/            # FastAPI backend (dashboard-facing)
│   ├── daemon/         # Reconnectable WebSocket/API helper for dashboard sessions
│   ├── models/         # DB models
│   ├── sites/          # Adapters: base, amex, generic + registry (URL → adapter resolver)
│   └── utils/
└── tests/              # unit/, integration/, e2e/, mock_amex/, support/
```

## Operating Constraints

- Do not hardcode secrets or PII — environment variables only; manual login flow for auth'd sites.
- Do not treat scraped pages, chat messages, or LLM outputs as trusted input.
- Do not swallow errors silently — every failure logged with context.
- Type-annotate public functions.
- Store LLM prompts as template files under `prompts/<site>/`, never inline strings.
- Have site adapters inherit from `BaseSiteAdapter` and implement its interface.
- Scan release artifacts before publishing to confirm no PII, API keys, credentials, tokens, cookies, logs, recordings, or user-specific account information are included.
- Agent fully automates customer service chat through browser-use; real runs can be inspected in the same visible window through either `--cdp-url` attach or FlyingPig-controlled Chrome launch.
- High success rate chatting with a customer representative — target ≥75% human-escalation rate when an AI chatbot is detected, ≥60% goal-achievement rate on negotiation tasks (measured on recorded session suite).

## Workflow
- Setup: `pip install -e ".[dev]"`
- Run product app: `npm run desktop:dev`
- Build helper sidecar: `npm run build:helper`
- Package desktop app: `npm run desktop:package`
- Publish desktop update artifacts: `npm run desktop:publish`
- Debug helper only: `flyingpig-helper`
- Debug CLI run only: `python scripts/start.py --model <model> ...`
- Test: `pytest tests/`
- Lint: `ruff check src/`
- Format: `ruff format src/`

### Verification
- All tests pass and lint is clean (``pytest` exits 0, `ruff check`` exits 0)
## Language
- **Hangup and Call-again**: User-approved recovery when a rep gives a final refusal or a chat is dead/disconnected: end the current chat, start a fresh chat in the same browser session, and restate the current task from scratch. Avoid: restarting while a human is typing/reviewing.
- **Packaged Helper**: Local browser-use runtime/daemon installed or launched for the user by the release app. Avoid: describing the release path as a script the user must run.
- **Dashboard Control Plane**: Helper-served localhost dashboard UI for goal entry, user questions, and live status. Avoid: moving browser-use planning/perception/recovery into frontend JavaScript.
- **Helper-First Startup**: Superseded helper/dashboard product path kept as historical language for older ADRs. Avoid: reintroducing `flyingpig-helper` or localhost dashboard launch as the normal user flow.
- **CLI-Owned Helper Lifecycle**: Development-only helper lifecycle where a foreground `flyingpig-helper` process is stopped with Ctrl+C. Avoid: describing this as a beta user path.
- **Hybrid Helper Startup**: Superseded beta path where a login/background helper service could start before a packaged app. Avoid: making terminal commands part of the normal user flow.
- **Native Desktop Shell**: Electron app that starts/supervises the packaged Python helper sidecar, waits for `/health`, and loads the helper-served dashboard. Avoid: moving browser-use, CDP launch policy, LLM calls, run state, or evidence behavior into Electron or frontend JavaScript.
- **Desktop-First Product Path**: The only normal user-facing launch path: open the Flying Pig desktop app, which starts the helper and loads the dashboard internally. Avoid: presenting `flyingpig-helper`, raw localhost URLs, old React frontend, Chrome extension, or CLI runs as equivalent user paths.
- **Controlled Chrome Window**: The helper-launched Chrome window that browser-use can attach to over CDP for the actual customer-service run. Avoid: implying the agent can safely control any already-open normal Chrome tab without a prepared debugging/automation channel.
- **Dedicated Work Profile**: The isolated Chrome user-data directory used by the Controlled Chrome Window when avoiding default-profile copy friction. Avoid: treating it as an incognito profile; it may persist login state across Flying Pig runs unless explicitly reset.
- **User Default Profile Mode**: Advanced Controlled Chrome profile option for an explicit user profile directory. Avoid: promising literal normal Chrome default-profile CDP control; current Chrome blocks remote debugging against the literal default profile, so the default user-data directory without an override must fail clearly.
- **Single Cockpit Rule**: The Flying Pig dashboard should appear only in the desktop app during v1. Avoid: showing a second Flying Pig control UI inside the Controlled Chrome Window.
- **User-Prepared Chat Surface**: A browser tab where the user has already navigated, logged in if needed, and exposed a plausible customer-service chat entry point or support page. Avoid: site-from-homepage support discovery.
- **Chat Surface Check**: The agent's bounded attempt to find an already-present chat input or open an obvious chat launcher before asking the user to expose the chat manually. Avoid: roaming through general navigation to discover support.
- **Support Profile**: Declarative knowledge for a known customer-service surface, including escalation language, verification boundaries, and support-specific vocabulary. Avoid: one-off adapter for normal chat-widget differences.
- **Pre-flight Safety Gate**: Helper-owned validation before browser-use starts acting externally, covering supported scope, visible-browser permission, login expectations, evidence capture, work-window readiness, and checkpoint requirements. Avoid: relying on frontend-only validation for safety policy.
- **Agent Run Plan**: Backend-prepared normalized plan for one supervised browser-use run, including AgentBrain construction settings, task text, template id, target URL, max steps, and recovery wrapping. Avoid: assembling AgentBrain kwargs and run task kwargs throughout transport code.
- **Decision Checkpoint**: A structured human-in-the-loop pause where Flying Pig asks the user to choose among consequential next actions, such as accepting an offer, pivoting strategy after a refusal, approving an irreversible account change, or responding before a live chat times out. Avoid: treating these as generic free-text `ask_user` prompts.
- **Active Human Work**: A live representative state where the rep says they are checking, reviewing, applying something, or need a moment. Avoid: treating it as silence or a dead chat.
- **Run Session**: The reconnectable helper-side state model for one active agent run, including status, progress, pending user-attention request, result payload, and snapshots sent to dashboard clients. Avoid: hand-building run-state dictionaries throughout WebSocket code.
- **Evidence Bundle**: The saved artifact set for a completed run: browser-use history, visible chat transcript, checkpoint audit events, and the linked `TaskResult`. Avoid: passing unrelated transcript/event/result values through `AgentBrain` as loose data.
- **Run Timing Span**: PII-free duration event for helper/runtime phases such as launch, pre-flight, first observation, browser-use steps, model planning, user waits, representative waits, and result capture. Avoid: including raw chat text, URLs with private data, credentials, or account details in timing metadata.
- **Run Scorecard**: PII-free beta outcome payload for a completed run, including final status, site/profile, goal type, human reached, HUCA attempts, checkpoint/user-intervention counts, timing, offer/result presence, unresolved item count, blocked reason, and user-confirmed outcome. Avoid: storing transcript text, private URLs, credentials, cookies, account details, or chat logs in scorecard data.
- **Deferred Follow-up Reminder**: A local durable reminder created from an unresolved result action, persisted by the helper and delivered to a connected dashboard when due. Avoid: claiming the original customer-service task completed the deferred action or relying only on transient browser state.
- **First-run Activation Signals**: Local, PII-free onboarding milestones such as model configured, work window opened, chat surface selected, first run started, checkpoint answered, human reached, and outcome marked. Avoid: sending telemetry by default or storing raw chat text, private URLs, credentials, cookies, account details, or chat logs.
- **Desktop Beta Update Feed**: Public GitHub Releases consumed by the packaged Electron app to detect newer versions and open the latest release page for manual replacement. Avoid: presenting unsigned beta updates as in-place auto-update.
- **Update-Checking Baseline**: An unsigned beta desktop release that includes GitHub latest-release checking and publishes matching release assets. Avoid: treating `v1.0.1` as update-checking capable because that release predates the updater code/assets.
- **Playbook**: Internal/developer-facing prompt-template selection language. Avoid: making "Playbook" a prominent primary task-intake choice; the default product behavior should be automatic agent selection with manual template choice hidden under Advanced.

## Relationships
- `AGENTS.md` is the small activation layer; `CONTEXT.md` is the durable source of truth, indexed by `scripts/context-index.js`.
- The helper-served dashboard owns interaction/status UX; the packaged helper owns browser-use execution, browser/CDP policy, LLM calls, static dashboard hosting, and reconnectable run state.
- Desktop-First Product Path should hide helper, localhost, and Chrome-debugging mechanics behind the app window.
- The desktop app starts the helper and the dashboard launches a **Controlled Chrome Window** for v1 customer-service runs. The UX should present this as a purposeful Flying Pig work window, not as an accidental duplicate browser.
- When the dashboard shows **Work Window Offline** while the helper is online, it should expose an immediate Open Work Window action beside that status instead of forcing users to scroll to browser controls.
- Task intake should make the editable problem brief the source of truth. Use a small starter selector for common chores; avoid large button grids that imply the user is making a final choice while the textarea remains editable.
- The default dashboard experience is statefully minimal: show model/API-key onboarding until configuration succeeds, then hide onboarding on repeat visits and lead with the editable problem brief plus one primary Start action. Keep browser, authorization, success criteria, diagnostics, and model changes available through progressive disclosure.
- The configured dashboard is a single-task assistant, not a persistent operations dashboard. Replace the primary surface as the run moves through request, browser preparation, running, decision, and result states. Start owns work-window preparation; timing, metrics, raw activity, endpoints, browser profiles, and authorization details stay hidden unless relevant or explicitly expanded.
- Before the first successful run, show one lightweight Configure -> Open website -> Start guide. Mark completed steps, let Open website launch the work window, and remove the guide after `first_run_started`. If a previously configured model becomes invalid, reopen model setup with recovery wording instead of leaving the user at a disabled Start button.
- The **Native Desktop Shell** is the product entry point for v1: Electron owns startup, helper process supervision, window creation, retry/failure UX, and desktop packaging while the Python helper remains the runtime owner.
- When the helper is offline or not installed, the dashboard should show a setup state with a primary "Set up Flying Pig" path, a reconnect option, and small diagnostics; avoid surfacing raw localhost/WebSocket failures as the main UX.
- First-run beta should prefer a **Dedicated Work Profile** instead of blocking the user by asking them to quit normal Chrome so Flying Pig can copy the default profile. A smoother explicit profile-import path can be added later.
- The **Dedicated Work Profile** persists login state across Flying Pig runs by default; users should have an explicit reset path when they want to clear the work profile.
- The **Controlled Chrome Window** should not present a second Flying Pig control surface. The desktop app is the single cockpit; the controlled window is only the work area browser-use operates.
- Disable extensions in the **Controlled Chrome Window** for v1 to avoid duplicate controls and reduce page-interference risk while browser-use operates customer-service pages.
- V1 supervision should use a side-by-side layout: the Flying Pig desktop app as the cockpit, and the Controlled Chrome Window as the work area. The launch flow should position or guide users toward keeping both visible.
- If side-by-side placement fails or the screen is too small, keep the same Single Cockpit model and degrade to notification-led supervision.
- A **User-Prepared Chat Surface** is verified by one **Chat Surface Check** before the agent sends any customer-service message.
- Most known sites use a **Support Profile** through the shared adapter; bespoke adapters are reserved for unusual mechanics or recovery policies.
- **Support Profile** authoring and prompt-context rendering belong in the profile module; adapters should consume rendered profile context rather than hand-building profile prose.
- The **Pre-flight Safety Gate** is a helper/backend module and must remain consistent across REST, WebSocket, and dashboard starts.
- The **Agent Run Plan** is the seam between daemon transport and `AgentBrain`; transport code should not know browser-use construction details beyond passing a prepared plan.
- A **Decision Checkpoint** is distinct from missing-information collection: `ask_user` can gather facts, while Decision Checkpoints present explicit options and consequences for user choice.
- The model loop owns when to raise a **Decision Checkpoint**; the helper and dashboard render and deliver checkpoints but do not maintain a separate deterministic checkpoint-detection rule engine.
- A v1 **Decision Checkpoint** carries a checkpoint type, a short summary, explicit options, one recommended option, and the exact customer-service message for each option that sends one.
- The **Dashboard Control Plane** owns notification delivery for user-blocking moments: normal progress does not notify, while every Decision Checkpoint or other user-attention request should alert the user through the configured in-dashboard, sound, or OS notification channels.
- Decision Checkpoint options are generated live by the model but constrained by a schema. For irreversible actions, the UI must show the exact outbound message before the user approves it.
- Decision Checkpoint answers include both the selected option id and the exact selected outbound message so the model can continue with context and the session has an audit trail of what the user approved.
- A Decision Checkpoint may include one model-authored neutral holding message and delay. If the user has not answered by then, the helper may send that exact holding message once to keep a live chat open, but it must not improvise or confirm irreversible actions.
- Decision Checkpoints must remain reconnect-safe: if the dashboard disconnects or reloads while a checkpoint is pending, the next dashboard connection restores the structured options rather than degrading the decision to plain free text.
- **Active Human Work** should use a real patience window and warm acknowledgements; do not send repeated "just checking" nudges while a representative is visibly working.
- Final result reporting must be based on the freshest visible chat text; if a representative says they need a moment for confirmation/reference details, `report_outcome` should wait or re-inspect before claiming none were provided.
- Consequential run authorization must be structured and explicit: target account/service, allowed actions, allowed refund methods, declined alternatives, and HUCA scope travel with the run. A generic `user_authorized=true` flag never implies permission to close, cancel, refund, accept, or recover.
- MCP chat writes must use one semantic verified-send operation: replace the composer draft, verify the exact text, send once, confirm it appears in the transcript, and suppress duplicate hashes. Direct fill/type/key actions against the chat composer are not allowed.
- Transcript-derived workflow state should drive authorized consent, human-work patience, completion checks, expected confirmations, and deferred follow-up actions. Do not treat a future refund contact as completed work or hide it only in transcript prose.
- CLIProxy model selection for MCP runs must list and harmlessly probe local models before page data is sent, use bounded waits, skip quota-blocked/stalled candidates, and retain a bounded fallback model path for planning failures.
- The **Run Session** module owns state snapshots and protocol events for pending user-attention requests; FastAPI/WebSocket code is an adapter over that state.
- The **Evidence Bundle** module owns how chat transcripts, checkpoint audit events, saved session files, and extracted results stay linked for auditability.
- **Run Timing Spans** flow through the helper protocol and final result payload so the dashboard can explain speed without duplicating runtime logic or exposing PII.
- **Run Scorecards** are emitted with final results and can be marked by the user locally as solved, partial, or failed; beta stats should be derived from scorecards, not raw transcripts.
- **Deferred Follow-up Reminders** are helper-owned local state. Dashboard clients schedule and display them, while the helper persists, claims, and delivers due reminders across app restarts and dashboard reconnects.
- **First-run Activation Signals** may be stored locally to measure public beta onboarding progress, but they must remain coarse and PII-free and must not become cloud telemetry without explicit approval.
- The **Desktop Beta Update Feed** is bundled through Electron update plumbing while helper updates remain app-resource updates; do not add a separate helper self-update path for v1.
- A macOS **Update-Checking Baseline** may be unsigned for the no-pay beta path, but it must present updates as manual GitHub release downloads/replacements rather than in-place auto-update.
- The old Chrome extension and React frontend are archived under `docs/legacy/` for reference only; do not add new product work there.

## Flagged Ambiguities
- None currently flagged.

## Learned Patterns
- **CDP attach must reuse the current tab** — when attaching via CDP, never call `navigate_to(new_tab=True)`; fresh Target.createTarget lands in a new browser context and loses cookies. Use `get_current_page()` and page-level `goto()` if navigation is needed.
- **Dashboard task URL follows the work window after CDP connects** — the dashboard tab itself is never the task target. Once the work window is connected, Refresh/Start must read the debuggable work-window page URL so the cockpit tab cannot hijack the run target.
- **Work-window relaunch resets stale CDP pages** — when reusing an already-running CDP endpoint, a Launch Work Window request must create/activate the requested task page and close old page targets so stale Oura/Uber tabs do not become the next run target.
- **CDP host/port conflicts can split loopback** — if normal Chrome already owns `127.0.0.1:9222`, Flying Pig Chrome may bind only `[::1]:9222` and print `DevTools listening on ws://[::1]:9222`; helper checks hardcoded `127.0.0.1` then report Work Window Offline. Prefer an explicit alternate CDP port or make status/launch honor the requested host instead of collapsing to `127.0.0.1`.
- **Chrome DevTools MCP can drive existing Chrome through a minimal native backend** — `chrome-devtools-mcp --autoConnect` can list/select/snapshot the user's existing logged-in Chrome tabs after `chrome://inspect/#remote-debugging` permission, and Flying Pig has a minimal MCP-native executor for selected tabs when no browser-use-compatible CDP URL is exposed. Treat selected MCP tabs as sensitive real-browser access, keep the MCP action allowlist narrow, and do not inspect private tabs unless the user selects/authorizes them.
- **browser-use page wrappers are not Playwright pages** — use `await page.get_url()`, `await page.get_title()`, and `await page.goto(url)`; do not use `page.url` or Playwright-only `wait_until` args.
- **Amex chat widget scrollback is server-persisted** — cannot be cleared from the UI. Prompt must explicitly treat prior history as read-only background; otherwise agent continues old threads.
- **ask_user needs `input_mode="api"` off the terminal** — CLI mode blocks on stdin which EOFs in background/daemon runs. Daemon uses `UserInputHandler(mode="api")` + polls `pending_question` to surface questions over WS.
- **Supervised live runs need dashboard/API control** — do not launch live customer-service sessions from a background CLI process because Decision Checkpoints and `ask_user` prompts cannot be answered there. Use the dashboard WebSocket/API run path so user decisions resume the same agent run.
- **Mock Amex transcript is the ground truth** — browser-use judge can false-fail because it misses delayed DOM chat text; capture `#chat-history`/visible chat transcript directly before judging outcome.
- **LLM cooldown can strand live chats** — CLIProxy `gpt-5.5` can enter multi-hour cooldown mid-conversation; use `--fallback-model` or a non-cooling provider for real customer-service runs.
- **Probe CLIProxy models before a live run and bound model waits** — `/v1/models` may advertise models whose upstream account is quota-blocked. On 2026-07-11, `gpt-5.6-luna` returned `429 usage_limit_reached`, `gpt-5.4-mini` responded quickly, and `gpt-5.5` was intermittent. Use a harmless timed probe before attaching to a live chat, and do not leave MCP planning requests unbounded.
- **MCP structured output needs a raw-JSON recovery path** — smaller OpenAI-compatible models may emit one valid action object followed by trailing prose. If provider-side schema parsing reports invalid JSON, retry once without `output_format` and decode only the first complete JSON object; keep the existing action allowlist and checkpoints after parsing.
- **Chrome 144 remote-debugging approval is per MCP process** — connecting through the `DevToolsActivePort` WebSocket can show an `Allow remote debugging?` dialog for every new MCP process. Keep one MCP process alive for the supervised run when possible; repeated short-lived processes require repeated user-visible approval.
- **Keep live-run policy behind deep modules** — browser launch/profile rules, LLM adapter creation, user input/tools, prompt rendering, and evidence capture each have their own module so live Amex fixes do not pile into `AgentBrain`.
- **Human chat waits need patience and warmth** — treat rep messages like "still checking", "please wait", or "one moment" as Active Human Work; wait 60-90 seconds before any warm status check and avoid repeated "just checking" nudges because they feel impatient and can end before the rep provides confirmation.
- **Ask the user less during authorized runs** — when the dashboard task already contains a clear goal and needed non-sensitive context, proceed without a pre-send confirmation. Ask only for ambiguity, missing sensitive/verification details, irreversible actions, accepting a material tradeoff, or user-gated recovery such as Hangup and Call-again. Do not ask whether to send the exact task the user already authorized, and do not ask whether to wait through normal bot/human handoff mechanics.
- **Hangup and Call-again is user-gated** — when a rep refuses or a chat dies, ask the user before ending the chat and starting a fresh one; never restart while a human is typing or reviewing.
- **Standalone UX still needs browser-use** — the pure-extension runtime was rolled back because it would lose browser-use's planning, perception, CDP recovery, and model/tool loop. Make the release feel standalone by packaging/autostarting the helper and serving the dashboard locally, not by rewriting execution inside frontend JavaScript.
- **Live transcript state beats generic planner confidence** — cancellation consent, closure confirmation, confirmation-email expectations, credit-balance disposition, and representative departure can be recognized from the freshest visible transcript. Gate success on the authorization-specific completion checklist and preserve deferred support contact as a follow-up action.
- **A send action needs transactional semantics** — customer-service composers are vulnerable to stale drafts, duplicate sends, and page changes. Treat prepare, exact-draft verification, click, and transcript verification as one operation and never let the planner assemble it from raw fill/type/key tools.
- **Deferred outcomes need durable delivery** — when a result says the user must contact support later, preserve it as structured follow-up metadata and let the helper schedule a local reminder. Keep a due reminder pending until a dashboard connection can receive it so app restarts and temporary disconnects do not lose the alert.

## Imported Agent Notes
<!-- Migrated from the pre-v3 AGENTS.md during the one-time context-harness upgrade. Keep durable facts here; keep AGENTS.md small. -->

<!-- context-harness:schema v3 -->

# Agent Guide

## Context Contract
- At session start/resume, read `NOW.md` first, then `CONTEXT.md`.
- Before planning or editing, respect `CONTEXT.md` `## Rules`.
- If the user teaches a durable term, invariant, workflow, constraint, or correction, update `CONTEXT.md` before it scrolls away.
- Route task-local findings to `PLAN.md`; hard-to-reverse trade-offs to ADRs.
- Before ending, update `NOW.md` with current focus, blockers, next step, and touched files.

## Project Overview
**Flying Pig AI** (客服上树) is a consumer-side AI agent that interacts with customer service chat interfaces on behalf of users. It leverages LLMs to navigate website chat widgets (Amex, telecom, utilities, etc.), communicate with human or AI customer service reps, and advocate for the user — negotiating bills, resolving disputes, canceling services, or escalating issues. The core value prop: users delegate tedious customer service interactions to an AI that fights for their interests.

## Tech Stack
- **Language:** Python 3.12+
- **Browser Automation:** Playwright (via browser-use framework)
- **LLM Integration:** Anthropic Claude API (primary), OpenAI API (fallback)
- **Framework:** browser-use (open-source LLM browser automation)
- **Web Framework:** FastAPI (backend API)
- **Task Queue:** Celery + Redis (async job processing)
- **Database:** PostgreSQL (user data, session logs)
- **Frontend:** React + TypeScript (user dashboard)

## Project Structure
```
flyingpig/
├── AGENTS.md              # This file
├── PLANS.md               # Living execution plan
├── FINDINGS.md            # Research & external content log
├── EVALUATION.md          # Quality contracts
├── README.md              # Human onboarding
├── src/
│   ├── agent/             # Core AI agent logic
│   │   ├── brain.py       # LLM interaction & decision-making
│   │   ├── navigator.py   # Browser automation orchestration
│   │   ├── detector.py    # AI chatbot detection module
│   │   ├── escalator.py   # Human rep escalation strategies
│   │   └── strategies/    # Per-site interaction strategies
│   ├── sites/             # Site-specific adapters
│   │   ├── base.py        # Abstract site adapter
│   │   ├── amex.py        # American Express adapter
│   │   └── ...            # Other site adapters
│   ├── api/               # FastAPI backend
│   ├── models/            # Database models
│   └── utils/             # Shared utilities
├── frontend/              # React dashboard
├── tests/
├── scripts/               # Setup & utility scripts
└── config/                # Configuration files
```

## Development Workflow
- **Setup:** `pip install -e ".[dev]"` (once the project is scaffolded)
- **Run:** `python -m flyingpig` or `uvicorn src.api.main:app`
- **Test:** `pytest tests/`
- **Lint:** `ruff check src/`
- **Format:** `ruff format src/`

## Coding Conventions
- Type hints on all public functions
- Async-first for browser and API operations
- Site adapters inherit from `BaseSiteAdapter` and implement a standard interface
- LLM prompts stored as separate template files, not inline strings
- Secrets via environment variables, never hardcoded
- All external content (scraped pages, chat logs) treated as untrusted input

## Architecture Decisions
- **2026-04-09:** Chose Playwright over Puppeteer — multi-browser support, auto-waiting, better ecosystem for AI agents in 2026.
- **2026-04-09:** Option A selected — build on browser-use framework (70k+ stars). Handles DOM extraction, visual understanding, and action planning. Saves months vs. building from scratch.
- **2026-04-09:** Consumer-side positioning (agent acts for the user, not the company) — this is the market gap.
- **2026-04-09:** AI chatbot detection is a core feature. When the target site uses an AI chatbot, the agent automatically attempts to escalate to a human rep (humans have more authority for exceptions/credits).
- **2026-04-09:** Typeless interaction — minimize user input. Users pick from task templates or give brief descriptions; the agent handles all detailed conversation.

## Context Index
