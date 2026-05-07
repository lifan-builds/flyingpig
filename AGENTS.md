# Agent Guide

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
