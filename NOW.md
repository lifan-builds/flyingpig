# Now

## Current Focus
Post-Oura reflection patch: successful live run exposed that Flying Pig was checking with the user too often. Prompts and runtime policy now tell the agent to proceed on already-authorized clear dashboard tasks, while still asking for ambiguity, sensitive verification, irreversible actions, material tradeoffs, and user-gated recovery.

## Active Blockers
- Normal Chrome dashboard tab was difficult to open through automation because the Chrome backend blocks direct `chrome-extension://` navigation and toolbar accessibility actions were flaky; manual dashboard launch remains worth checking before inviting beta testers.
- Publishing/tagging the release has not been done in this session.

## Immediate Next Step
Use Uber Eats as the next supervised live example after push: user will log in, then Flying Pig should ask for a refund or compensation on a recent pickup order because it was ordered at 5:30, ready only at 6:15, and the store said the ordered drink was sold out and exchanged it for another drink type.

## Session State
- Last modified: 2026-05-18
- Files touched: CONTEXT.md, NOW.md, PLAN.md, README.md, docs/beta.md, docs/adr/0002-extension-first-single-cockpit.md, extension/manifest.json, extension/src/background.js, extension/src/dashboard.css, extension/src/dashboard.html, extension/src/dashboard.js, extension/src/dashboard_protocol.js, extension/src/setup.html, extension/src/sidepanel.html, package.json, prompts/amex/base.txt, prompts/generic/base.txt, prompts/shared/decision_checkpoints.txt, scripts/build_beta_release.py, scripts/daemon.py, scripts/start.py, scripts/test_dashboard_protocol.mjs, scripts/test_extension_dashboard.mjs, src/agent/brain.py, src/agent/user_input.py, src/daemon/server.py, src/helper.py, src/helper_service.py, tests/support/extension_daemon.py, tests/unit/test_amex_adapter.py, tests/unit/test_daemon_server.py, tests/unit/test_registry.py, tests/unit/test_user_input.py
- Verification: `pytest tests/unit/test_registry.py tests/unit/test_amex_adapter.py tests/unit/test_user_input.py -q`; `ruff check src/agent/brain.py tests/unit/test_registry.py tests/unit/test_amex_adapter.py`; prior `pytest tests/unit/test_user_input.py -q`; prior `ruff check src/agent/user_input.py src/agent/brain.py tests/unit/test_user_input.py`; previous `ruff check src scripts tests`; `pytest tests/unit/test_browser_runtime.py tests/unit/test_daemon_server.py -q`; `node scripts/test_dashboard_protocol.mjs`; elevated `npm run test:extension`; `git diff --check`.
- Live evidence: failed pre-patch Oura run `recordings/session_oura_ring_20260518_035222.json`; successful patched Oura run `recordings/session_oura_ring_20260518_041226.json` with reference chat `6847916`.
