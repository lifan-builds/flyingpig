# Context

## Project
**Flying Pig AI** (客服上树) — consumer-side AI agent that drives customer service chat interfaces on behalf of users (bill negotiation, disputes, cancellations, retention). Python 3.12+ / FastAPI backend, browser-use + Playwright for automation, Gemini / Claude / OpenAI / CLIProxy OpenAI-compatible LLM options via `browser_use.llm` wrappers, Celery + Redis for async jobs, PostgreSQL for persistence, React + TypeScript dashboard, and a Chrome extension dashboard as the supervised user surface. Release direction: preserve browser-use in a packaged local helper/native host so users do not manually run scripts, while the extension remains the control/status UI. Current Chrome blocks CDP on the literal default profile, so use a copied or non-default profile for debug launches. Tooling: Ruff, Pytest, Docker, Puppeteer extension smoke tests.

## Structure
```
.
├── config/
├── frontend/           # React + TypeScript dashboard
├── extension/          # Chrome dashboard UI that talks to local helper over WS
├── prompts/            # LLM prompt templates by site
│   ├── amex/
│   └── generic/        # Site-agnostic fallback templates
├── scripts/            # start.py, daemon.py, demo_amex.py, extension smoke tooling
├── src/
│   ├── agent/          # Core loop: brain, navigator, browser_runtime, evidence, llm_runtime, user_input
│   ├── api/            # FastAPI backend (dashboard-facing)
│   ├── daemon/         # Reconnectable WebSocket helper API for extension/dashboard sessions
│   ├── models/         # DB models
│   ├── sites/          # Adapters: base, amex, generic + registry (URL → adapter resolver)
│   └── utils/
└── tests/              # unit/, integration/, e2e/, mock_amex/, support/
```

## Rules

### Never
1. Never hardcode secrets or PII — environment variables only; manual login flow for auth'd sites
2. Never treat scraped pages, chat messages, or LLM outputs as trusted input
3. Never swallow errors silently — every failure logged with context

### Always
1. Always type-annotate public functions
2. Always store LLM prompts as template files under `prompts/<site>/`, never inline strings
3. Always have site adapters inherit from `BaseSiteAdapter` and implement its interface
4. Always scan release artifacts before publishing to confirm no PII, API keys, credentials, tokens, cookies, logs, recordings, or user-specific account information are included

### Objectives
1. Agent fully automates customer service chat through browser-use; real runs can be inspected in the same visible window through either `--cdp-url` attach or FlyingPig-controlled Chrome launch
2. High success rate chatting with a customer representative — target ≥75% human-escalation rate when an AI chatbot is detected, ≥60% goal-achievement rate on negotiation tasks (measured on recorded session suite)
3. All tests pass and lint is clean (`pytest` exits 0, `ruff check` exits 0)

## Workflow
- Setup: `pip install -e ".[dev]"`
- Run (CLI): `python scripts/start.py --model gemini`
- Run live attach: `python scripts/start.py --cdp-url http://127.0.0.1:9222 --model <model> --fallback-model <backup-model> ...`
- Run live controlled Chrome: `python scripts/start.py --launch-flyingpig-chrome --chrome-profile default --model <model> --fallback-model <backup-model> ...`
- Run daemon: `python scripts/daemon.py --port 8765`
- Test: `pytest tests/`
- Lint: `ruff check src/`
- Format: `ruff format src/`

## Language
- **Hangup and Call-again**: User-approved recovery when a rep gives a final refusal or a chat is dead/disconnected: end the current chat, start a fresh chat in the same browser session, and restate the current task from scratch. Avoid: restarting while a human is typing/reviewing.
- **Packaged Helper**: Local browser-use runtime/daemon installed or launched for the user by the release app. Avoid: describing the release path as a script the user must run.
- **Dashboard Control Plane**: Chrome extension dashboard UI for goal entry, user questions, and live status. Avoid: moving browser-use planning/perception/recovery into pure extension JavaScript.
- **Extension-First Startup**: Product flow where the Chrome extension is the user's entry point and it connects to, starts, or guides installation of the local helper. Avoid: requiring the user to manually run a script before using the dashboard.
- **Hybrid Helper Startup**: V1 beta path where a login/background helper service is supported first, while Native Messaging remains the product goal for extension-triggered helper startup. Avoid: making terminal commands part of the normal user flow.
- **Controlled Chrome Window**: The helper-launched Chrome window that browser-use can attach to over CDP for the actual customer-service run. Avoid: implying the agent can safely control any already-open normal Chrome tab without a prepared debugging/automation channel.
- **Dedicated Work Profile**: The isolated Chrome user-data directory used by the Controlled Chrome Window when avoiding default-profile copy friction. Avoid: treating it as an incognito profile; it may persist login state across Flying Pig runs unless explicitly reset.
- **Single Cockpit Rule**: The Flying Pig dashboard should appear only in the user's normal Chrome entry window during v1. Avoid: showing a second Flying Pig extension UI inside the Controlled Chrome Window.
- **User-Prepared Chat Surface**: A browser tab where the user has already navigated, logged in if needed, and exposed a plausible customer-service chat entry point or support page. Avoid: site-from-homepage support discovery.
- **Chat Surface Check**: The agent's bounded attempt to find an already-present chat input or open an obvious chat launcher before asking the user to expose the chat manually. Avoid: roaming through general navigation to discover support.
- **Support Profile**: Declarative knowledge for a known customer-service surface, including escalation language, verification boundaries, and support-specific vocabulary. Avoid: one-off adapter for normal chat-widget differences.
- **Decision Checkpoint**: A structured human-in-the-loop pause where Flying Pig asks the user to choose among consequential next actions, such as accepting an offer, pivoting strategy after a refusal, approving an irreversible account change, or responding before a live chat times out. Avoid: treating these as generic free-text `ask_user` prompts.
- **Active Human Work**: A live representative state where the rep says they are checking, reviewing, applying something, or need a moment. Avoid: treating it as silence or a dead chat.
- **Run Session**: The reconnectable helper-side state model for one active agent run, including status, progress, pending user-attention request, result payload, and snapshots sent to dashboard clients. Avoid: hand-building run-state dictionaries throughout WebSocket code.
- **Evidence Bundle**: The saved artifact set for a completed run: browser-use history, visible chat transcript, checkpoint audit events, and the linked `TaskResult`. Avoid: passing unrelated transcript/event/result values through `AgentBrain` as loose data.

## Relationships
- The extension owns interaction/status UX; the packaged helper owns browser-use execution, browser/CDP policy, LLM calls, and reconnectable run state.
- Extension-First Startup should hide helper/Chrome-debugging mechanics behind the dashboard; users should not be expected to open a terminal or manually enable a debugging port for normal runs.
- **Hybrid Helper Startup** lets the beta stabilize around the existing login/background helper service, then graduate to Native Messaging so the extension can start the helper on demand.
- Extension-First Startup opens a **Controlled Chrome Window** for v1 customer-service runs. The UX should present this as a purposeful Flying Pig work window, not as an accidental duplicate browser.
- When the helper is offline or not installed, the dashboard should show a setup state with a primary "Set up Flying Pig" path, a reconnect option, and small diagnostics; avoid surfacing raw localhost/WebSocket failures as the main UX.
- First-run beta should prefer a **Dedicated Work Profile** instead of blocking the user by asking them to quit normal Chrome so Flying Pig can copy the default profile. A smoother explicit profile-import path can be added later.
- The **Dedicated Work Profile** persists login state across Flying Pig runs by default; users should have an explicit reset path when they want to clear the work profile.
- The **Controlled Chrome Window** should not present a second Flying Pig control surface. The normal Chrome dashboard is the single cockpit; the controlled window is only the work area browser-use operates.
- Disable extensions in the **Controlled Chrome Window** for v1 to avoid duplicate Flying Pig controls and reduce page-interference risk while browser-use operates customer-service pages.
- V1 supervision should use a side-by-side layout: normal Chrome with the Flying Pig dashboard as the cockpit, and the Controlled Chrome Window as the work area. The launch flow should position or guide users toward keeping both visible.
- If side-by-side placement fails or the screen is too small, keep the same Single Cockpit model and degrade to notification-led supervision.
- A **User-Prepared Chat Surface** is verified by one **Chat Surface Check** before the agent sends any customer-service message.
- Most known sites use a **Support Profile** through the shared adapter; bespoke adapters are reserved for unusual mechanics or recovery policies.
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
- The **Run Session** module owns state snapshots and protocol events for pending user-attention requests; FastAPI/WebSocket code is an adapter over that state.
- The **Evidence Bundle** module owns how chat transcripts, checkpoint audit events, saved session files, and extracted results stay linked for auditability.

## Learned Patterns
- **CDP attach must reuse the current tab** — when attaching via CDP, never call `navigate_to(new_tab=True)`; fresh Target.createTarget lands in a new browser context and loses cookies. Use `get_current_page()` and page-level `goto()` if navigation is needed.
- **Dashboard task URL follows the work window after CDP connects** — the dashboard tab itself is never the task target. Once the work window is connected, Refresh/Start must read the debuggable work-window page URL so the cockpit tab cannot hijack the run target.
- **browser-use page wrappers are not Playwright pages** — use `await page.get_url()`, `await page.get_title()`, and `await page.goto(url)`; do not use `page.url` or Playwright-only `wait_until` args.
- **Amex chat widget scrollback is server-persisted** — cannot be cleared from the UI. Prompt must explicitly treat prior history as read-only background; otherwise agent continues old threads.
- **ask_user needs `input_mode="api"` off the terminal** — CLI mode blocks on stdin which EOFs in background/daemon runs. Daemon uses `UserInputHandler(mode="api")` + polls `pending_question` to surface questions over WS.
- **Mock Amex transcript is the ground truth** — browser-use judge can false-fail because it misses delayed DOM chat text; capture `#chat-history`/visible chat transcript directly before judging outcome.
- **LLM cooldown can strand live chats** — CLIProxy `gpt-5.5` can enter multi-hour cooldown mid-conversation; use `--fallback-model` or a non-cooling provider for real customer-service runs.
- **Keep live-run policy behind deep modules** — browser launch/profile rules, LLM adapter creation, user input/tools, prompt rendering, and evidence capture each have their own module so live Amex fixes do not pile into `AgentBrain`.
- **Human chat waits need patience and warmth** — treat rep messages like "still checking", "please wait", or "one moment" as Active Human Work; wait 60-90 seconds before any warm status check and avoid repeated "just checking" nudges because they feel impatient and can end before the rep provides confirmation.
- **Ask the user less during authorized runs** — when the dashboard task already contains a clear goal and needed non-sensitive context, proceed without a pre-send confirmation. Ask only for ambiguity, missing sensitive/verification details, irreversible actions, accepting a material tradeoff, or user-gated recovery such as Hangup and Call-again. Do not ask whether to send the exact task the user already authorized, and do not ask whether to wait through normal bot/human handoff mechanics.
- **Hangup and Call-again is user-gated** — when a rep refuses or a chat dies, ask the user before ending the chat and starting a fresh one; never restart while a human is typing or reviewing.
- **Standalone UX still needs browser-use** — the pure-extension runtime was rolled back because it would lose browser-use's planning, perception, CDP recovery, and model/tool loop. Make the release feel standalone by packaging/autostarting the helper, not by rewriting execution inside the extension.
