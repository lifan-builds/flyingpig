# Now

## Current Focus
Beta hardening resumed from a clean Chrome/dependency state. Dependencies were reinstalled, the helper/dashboard pass was completed, and work-window relaunch now resets stale CDP page targets before reporting ready.

## Active Blockers
- Publishing/tagging the release has not been done in this session.

## Immediate Next Step
Review, commit, and push the beta-hardening changes. Optional follow-up before the small-group invite: add an Uber Eats support profile for more repeatable refund/credits runs.

## Session State
- Last modified: 2026-05-18
- Files touched: CONTEXT.md, NOW.md, README.md, docs/beta.md, extension/src/dashboard.js, src/agent/browser_runtime.py, src/daemon/run_session.py, src/daemon/server.py, tests/unit/test_browser_runtime.py, tests/unit/test_daemon_server.py.
- Verification: `pytest tests/unit/test_daemon_server.py -q`; `pytest tests/unit/test_browser_runtime.py tests/unit/test_daemon_server.py -q`; `ruff check src/agent/browser_runtime.py src/daemon/server.py src/daemon/run_session.py tests/unit/test_browser_runtime.py tests/unit/test_daemon_server.py`; `node scripts/test_dashboard_protocol.mjs`; elevated `npm run test:extension`; `python scripts/build_beta_release.py --clean`; beta zip privacy scan with `zipgrep`; `git diff --check`.
- Manual dashboard pass: normal Chrome extension dashboard opens; helper online/offline state renders; Start stays disabled while Work Window is offline; Launch Work Window connects controlled Chrome and dashboard follows the work-window URL; relaunch against an existing CDP endpoint leaves one page target for the intended support page.
