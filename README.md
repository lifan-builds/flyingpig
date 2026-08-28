# Flying Pig AI (客服上树)

An AI-powered agent that interacts with customer service chat interfaces on your behalf. Stop waiting on hold, arguing with chatbots, or navigating phone trees — let Flying Pig handle it.

## Deprecated

Flying Pig has been useful while the agent computer use capability wasn't that
strong, and it kept breaking while interacting with different vendors. But now,
with the latest Codex computer use and browser use, we feel this project is no
longer providing additional value over the native capabilities, so we are
deprecating it.

The repository is archived and no longer maintained. For this workflow, use
Codex's native computer use and browser use capabilities instead.

![Flying Pig agent history](agent_history.gif)

## Status

Flying Pig is an early local beta for supervised customer-service automation
that is no longer maintained. The usage and development instructions below are
retained for historical reference only; they are not a supported product path.

The current product shape is a native desktop app that starts a local Python
helper, opens the helper-served dashboard as the cockpit, and keeps the
Controlled Chrome Window separate as the work area. You prepare the support
page, start a run, watch progress from the dashboard, and approve consequential
decisions before the agent sends them.

## What It Does

Flying Pig AI acts as your personal customer service advocate. Give it a task ("negotiate my Amex annual fee down" or "cancel my cable subscription") and it will:

1. Navigate to the company's chat interface
2. Communicate with customer service (human or AI) on your behalf
3. Negotiate, dispute, or request what you need
4. Report back with the outcome and a full transcript

## Safety Model

- **User-prepared sessions** - you log in, handle MFA, and expose the chat surface before the agent acts.
- **Controlled work browser** - Flying Pig uses a dedicated or copied Chrome profile instead of taking over your everyday browser.
- **Decision checkpoints** - the dashboard asks before irreversible actions, accepting offers, changing strategy, or sending sensitive information.
- **Evidence bundle** - completed runs keep the transcript, checkpoint decisions, and final result together for review.

Flying Pig is not a background bot for unsupervised account changes. It is a
local, human-in-the-loop assistant for support conversations you already
authorized.

## Getting Started

### Public Mac Beta

1. Download the latest `Flying-Pig-*-arm64-mac.zip` from
   [GitHub Releases](https://github.com/lifan-builds/flyingpig/releases).
2. Unzip it and open `Flying Pig.app`.
3. If macOS blocks the unsigned beta, approve it from **System Settings ->
   Privacy & Security**, then open the app again.
4. In the app, choose a model provider and save an API key. Keys are written
   only to your local `~/.flyingpig/.env` file and are never displayed back.
5. Click **Open Work Window**, log in or handle MFA there, and navigate to the
   support page or chat you want Flying Pig to handle.
6. Pick a brief starter or write the customer-service goal yourself, then press
   **Start**. Keep the desktop app open for checkpoints and approvals.

The current no-pay Mac beta is unsigned. The app checks GitHub Releases for
newer versions and opens the release page when an update is available, but users
manually download and replace the app. This is not in-place auto-update.

See `docs/public-beta-quickstart.md` for the short user guide.

### Development Prerequisites
- Python 3.12+
- Node.js 20+ (for the desktop shell)
- Google Chrome
- A local CLIProxyAPI setup, or a provider API key

### Development Installation

```bash
git clone https://github.com/lifan-builds/flyingpig.git
cd flyingpig
pip install -e ".[dev]"
playwright install
```

### Development Configuration

Copy the example environment file and fill in your API keys:

```bash
cp .env.example .env
```

### Run The App

The desktop app is the only normal product entry point:

```bash
npm install
npm run desktop:dev
```

The desktop app chooses an available local helper port, starts the Python helper
without opening a browser tab, waits for `/health`, then loads the dashboard in
the app window. Click **Open Work Window** from the dashboard when you are
ready to prepare the customer-service tab.

For packaged builds, create the helper sidecar first and then package Electron:

```bash
npm run build:helper
npm run desktop:package
```

The current macOS packaging target is `.zip`. DMG packaging is intentionally not
enabled until the local native-addon signing issue in the DMG license toolchain
is resolved.

The packaged app must be scanned before release for PII, API keys, credentials,
tokens, cookies, logs, recordings, and user-specific account data.

By default, the app uses local CLIProxyAPI via `DEFAULT_LLM=cliproxyapi`.
It reads `CLIPROXYAPI_API_KEY` from `.env` if set, otherwise it falls back
to the first `sk-local-...` key in `~/.cli-proxy-api/config.yaml`.

For direct providers, set `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or
`GOOGLE_API_KEY` in `.env` depending on which model you pick. The desktop
dashboard also lets users save or clear a provider key from the first-run model
setup panel. The dashboard never displays saved keys; it writes them to the
user-local env file at `~/.flyingpig/.env`.

### Manual End-To-End Smoke

1. Open the Flying Pig app with `npm run desktop:dev`.

2. Press **Open Work Window**.

3. In the FlyingPig work window, open or prepare the Amex
customer-service tab. The dashboard remains the cockpit; the work window
runs without extensions.

4. Choose a brief starter or edit the task directly, then start. The dashboard streams
browser-use progress and forwards mid-run questions.

For supervised live runs, use the desktop app instead of a background
`scripts/start.py` process. If the agent hits a Decision Checkpoint, the app can
answer it and resume the same run; a background CLI process cannot read
interactive input.

The dashboard shows two separate statuses:

- **Helper Online** means the local WebSocket/API helper is reachable.
- **Work Window Connected** means a CDP-controlled Chrome window is reachable.

Start is disabled until both are online. This avoids the confusing case
where the dashboard is open in normal Chrome but browser-use cannot attach
to a controllable browser.

The desktop app is the intended beta entry point. The beta work window uses a
dedicated Flying Pig profile by default so setup does not ask users to quit
normal Chrome. To test the copied-profile path, use the work-window profile
picker in the app.

### Development Commands

These are developer/test surfaces, not separate product entry points:

```bash
ruff check src scripts tests
pytest tests -q -m "not slow"
npm run test:dashboard
npm run test:desktop
```

`npm run test:dashboard` is a fast protocol/UI smoke for the helper-served
dashboard. `npm run test:desktop` checks that the native shell can supervise the
helper and reach the dashboard.

Advanced helper/CLI entry points remain for debugging only:

```bash
flyingpig-helper
flyingpig-helper --open-dashboard
python scripts/start.py --help
python scripts/daemon.py --help
```

See `docs/beta.md` for the first-cohort beta checklist and operating
rules.

## Development

```bash
# Run tests
pytest tests/

# Lint
ruff check src/

# Format
ruff format src/
```

## Project Structure

```
src/
├── agent/          # Core AI agent (LLM + browser automation)
├── sites/          # Per-site adapters (Amex, etc.)
├── daemon/         # Helper API, WebSocket protocol, dashboard static host
├── config.py        # Provider and runtime settings
dashboard/          # Helper-served cockpit loaded by the desktop app
desktop/            # Electron shell and helper supervision
docs/legacy/        # Archived old extension and React frontend references
tests/              # Test suite
```

## Supported Sites

- American Express (Amex) — in development
- More coming soon

## License

TBD
