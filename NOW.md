# Now

## Current Focus
Helper-first dashboard refactor completed with CLI-owned lifecycle. The beta cockpit lives in `dashboard/` and is served by `flyingpig-helper` at `/dashboard/`; the helper opens the dashboard, waits in the foreground, and users stop it with Ctrl+C.

## Active Blockers
- Public-site LLM submissions were intentionally not sent; CLIProxy-powered LLM execution was verified against the local mock Amex server.
- Publishing/tagging the release has not been done in this session.

## Immediate Next Step
Announce or tag the helper-first dashboard beta release. Optional follow-up: add a deterministic chat-surface fixture or test profile for public widget patterns so external-site compatibility can be regression-tested without live public-site submissions.

## Session State
- Last modified: 2026-05-19
- Files touched: CONTEXT.md, PLAN.md, NOW.md, README.md, docs/beta.md, docs/adr/0002-extension-first-single-cockpit.md, docs/adr/0003-helper-first-localhost-dashboard.md, dashboard/*, package.json, scripts/build_beta_release.py, scripts/test_dashboard_protocol.mjs, scripts/test_helper_dashboard.mjs, src/daemon/server.py, src/helper.py, src/helper_service.py, src/agent/decision_checkpoint.py, src/agent/navigator.py, tests/support/dashboard_daemon.py, tests/unit/test_daemon_server.py, tests/unit/test_helper_service.py.
- Verification: `ruff check src scripts tests`; `pytest tests -q -m "not slow"` (123 passed, 2 deselected); elevated `npm run test:dashboard`; CLIProxyAPI model check against `127.0.0.1:8317`; `python scripts/run_mock_amex.py --headless --model cliproxyapi --max-steps 18 --llm-timeout 240 --save-dir recordings/mock_run` succeeded with confirmation `MOCK-12345`; `python scripts/build_beta_release.py --clean`; beta zip content check confirmed `dashboard/` included and `extension/` absent; beta zip privacy scan with `zipgrep`; `git diff --check`.
- External chat-surface pass: LiveChat and Olark public widgets loaded, opened, and accepted harmless draft text without sending. Several other public sites produced support/product-link false positives for text-only detection, reinforcing that browser-use visual/model selection should own live chat-surface choice.
