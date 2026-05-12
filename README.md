# Flying Pig AI (客服上树)

An AI-powered agent that interacts with customer service chat interfaces on your behalf. Stop waiting on hold, arguing with chatbots, or navigating phone trees — let Flying Pig handle it.

## What It Does

Flying Pig AI acts as your personal customer service advocate. Give it a task ("negotiate my Amex annual fee down" or "cancel my cable subscription") and it will:

1. Navigate to the company's chat interface
2. Communicate with customer service (human or AI) on your behalf
3. Negotiate, dispute, or request what you need
4. Report back with the outcome and a full transcript

## Getting Started

### Prerequisites
- Python 3.12+
- Node.js 20+ (for frontend)
- PostgreSQL 16+
- Redis (for task queue)
- A local CLIProxyAPI setup, or a provider API key

### Installation

```bash
git clone <repo-url>
cd flyingpig
pip install -e ".[dev]"
playwright install
```

### Configuration

Copy the example environment file and fill in your API keys:

```bash
cp .env.example .env
```

### Usage

#### Option A: Docker Compose (Recommended)
You can launch the entire stack (PostgreSQL + API + React Frontend) using Docker:
```bash
docker-compose up --build
```
Access the application at `http://localhost:8000`.

#### Option B: Local Development
```bash
# Start the API server
uvicorn src.api.main:app --reload

# Start the frontend (in another terminal)
cd frontend && npm run dev
```

#### Option C: Friendly supervised launch

```bash
python scripts/start.py
```

This launches a FlyingPig-controlled Chrome using a persistent copy of
your default Chrome profile, opens Amex plus the local dashboard, waits
for you to log in or prepare the visible Amex tab, then attaches the
agent to that same tab. The copied profile lives at
`~/.flyingpig/chrome-cdp-default-copy/` so login can persist across runs
without attaching CDP to the literal live Chrome profile that modern
Chrome blocks.

Common choices stay short:

```bash
python scripts/start.py --template dispute_charge
python scripts/start.py --task "Ask Amex about my Oura Ring benefit credit."
python scripts/start.py --model cliproxyapi --fallback-model gemini-flash
```

If you want a clean isolated profile instead, pass `--chrome-profile
dedicated`. The first copied-profile launch should be created with normal
Chrome quit; after that, the copy can be launched independently.

Current Chrome builds block remote debugging on the literal default user
profile. Use `--chrome-profile default` for FlyingPig's persistent copied
profile, or provide a non-default `--chrome-user-data-dir`.

By default, the app uses local CLIProxyAPI via `DEFAULT_LLM=cliproxyapi`.
It reads `CLIPROXYAPI_API_KEY` from `.env` if set, otherwise it falls back
to the first `sk-local-...` key in `~/.cli-proxy-api/config.yaml`.

For direct providers, set `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or
`GOOGLE_API_KEY` in `.env` depending on which `--model` you pick.

#### Option D: Attach to an existing remote-debugging tab

The agent can also attach to a Chrome window that you started with a
remote-debugging port. This is the existing-tab path.

**Setup (once):** quit Chrome, then relaunch it with the remote-debugging
port open. Use a dedicated user-data dir so it doesn't conflict with your
normal profile:

```bash
# macOS example
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/flyingpig-chrome
```

**Run a task:**

1. In that Chrome window, log in to Amex and navigate to the chat page
   (e.g. https://www.americanexpress.com/us/customer-service/contact-us/
   and click "Chat With Us"). Make sure that tab is the active one.
2. In a terminal:

```bash
python scripts/start.py \
  --attach http://localhost:9222 \
  --template general \
  --model cliproxyapi \
  --fallback-model gemini-flash \
  --task "Ask Amex about my Oura Ring benefit credit."
```

The agent attaches to whatever tab is currently focused and operates from
there — it will not navigate away or open new tabs. Your cookies, login,
and MFA state come for free. On exit, the agent detaches; the browser
stays open.

### Chrome Extension Side Panel

The preferred supervised UI is the Chrome side panel. It keeps agent
status, questions, and controls visible beside the Amex tab while the
local Flying Pig helper runs the browser-use agent.

For beta, install the local helper service first. It starts the WebSocket
helper in the background at login; the side panel can then launch a
FlyingPig-controlled Chrome window when you are ready:

```bash
flyingpig-macos-helper install
```

1. In Chrome, open `chrome://extensions`, enable developer mode, click
**Load unpacked**, and select `extension/`.

2. Click the Flying Pig extension icon and press **Launch Chrome**.

3. In the FlyingPig Chrome window, open or prepare the Amex
customer-service tab.

4. Choose a playbook, edit the task, and start. The side panel streams
browser-use progress and forwards mid-run questions.

If the copied default Chrome profile has not been created yet, quit
normal Chrome once and press **Launch Chrome** again. To use a clean
profile that can run alongside normal Chrome during development, use:

```bash
flyingpig-helper --chrome-profile dedicated
```

For beta support:

```bash
flyingpig-macos-helper status
flyingpig-macos-helper stop
flyingpig-macos-helper start
flyingpig-macos-helper uninstall
```

Automated extension tests should use a Puppeteer-managed browser with the
extension installed through Puppeteer's extension APIs.

To run the deterministic mock side-panel smoke:

```bash
npm install
npm run test:extension
```

This launches a Puppeteer-managed Chrome with the unpacked extension,
starts mock Amex and helper servers, and verifies that the side panel can
start a browser-use-helper run and render progress.

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
├── api/            # FastAPI backend
├── models/         # Database models
└── utils/          # Shared utilities
frontend/           # React + TypeScript dashboard
tests/              # Test suite
config/             # Configuration files
```

## Supported Sites

- American Express (Amex) — in development
- More coming soon

## License

TBD
