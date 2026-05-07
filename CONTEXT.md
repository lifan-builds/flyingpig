# Context

## Project
**Flying Pig AI** (客服上树) — consumer-side AI agent that drives customer service chat interfaces on behalf of users (bill negotiation, disputes, cancellations, retention). Python 3.12+ / FastAPI backend, browser-use + Playwright for automation, Gemini / Claude / OpenAI / CLIProxy OpenAI-compatible LLM options via `browser_use.llm` wrappers, Celery + Redis for async jobs, PostgreSQL for persistence, React + TypeScript dashboard, and a Chrome side-panel extension as the supervised user surface. Release direction: preserve browser-use in a packaged local helper/native host so users do not manually run scripts, while the extension remains the control/status UI. Current Chrome blocks CDP on the literal default profile, so use a copied or non-default profile for debug launches. Tooling: Ruff, Pytest, Docker, Puppeteer extension smoke tests.

## Structure
```
.
├── config/
├── frontend/           # React + TypeScript dashboard
├── extension/          # Chrome side panel UI that talks to local helper over WS
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
- **Side Panel Control Plane**: Chrome extension UI for goal entry, user questions, and live status. Avoid: moving browser-use planning/perception/recovery into pure extension JavaScript.

## Relationships
- The extension owns interaction/status UX; the packaged helper owns browser-use execution, browser/CDP policy, LLM calls, and reconnectable run state.

## Learned Patterns
- **CDP attach must reuse the current tab** — when attaching via CDP, never call `navigate_to(new_tab=True)`; fresh Target.createTarget lands in a new browser context and loses cookies. Use `get_current_page()` and page-level `goto()` if navigation is needed.
- **browser-use page wrappers are not Playwright pages** — use `await page.get_url()`, `await page.get_title()`, and `await page.goto(url)`; do not use `page.url` or Playwright-only `wait_until` args.
- **Amex chat widget scrollback is server-persisted** — cannot be cleared from the UI. Prompt must explicitly treat prior history as read-only background; otherwise agent continues old threads.
- **ask_user needs `input_mode="api"` off the terminal** — CLI mode blocks on stdin which EOFs in background/daemon runs. Daemon uses `UserInputHandler(mode="api")` + polls `pending_question` to surface questions over WS.
- **Mock Amex transcript is the ground truth** — browser-use judge can false-fail because it misses delayed DOM chat text; capture `#chat-history`/visible chat transcript directly before judging outcome.
- **LLM cooldown can strand live chats** — CLIProxy `gpt-5.5` can enter multi-hour cooldown mid-conversation; use `--fallback-model` or a non-cooling provider for real customer-service runs.
- **Keep live-run policy behind deep modules** — browser launch/profile rules, LLM adapter creation, user input/tools, prompt rendering, and evidence capture each have their own module so live Amex fixes do not pile into `AgentBrain`.
- **Human chat needs slow waits** — after a rep joins or says they are reviewing, prefer 30-120 second waits and at most one short nudge; repeated 10-second waits burn step budget and look impatient.
- **Hangup and Call-again is user-gated** — when a rep refuses or a chat dies, ask the user before ending the chat and starting a fresh one; never restart while a human is typing or reviewing.
- **Standalone UX still needs browser-use** — the pure-extension runtime was rolled back because it would lose browser-use's planning, perception, CDP recovery, and model/tool loop. Make the release feel standalone by packaging/autostarting the helper, not by rewriting execution inside the extension.
