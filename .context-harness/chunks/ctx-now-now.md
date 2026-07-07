# Now

# Now

## Current Focus
Implemented and verified a minimal MCP-native existing-Chrome backend. Flying Pig can now Auto-Connect to an existing Chrome tab through Chrome DevTools MCP and run a minimal supervised backend without a browser-use/CDP handoff URL. Run payloads carry `browser_backend` and `mcp_page`; preflight accepts MCP-selected tabs; `AgentBrain` routes MCP runs to `McpBrowserExecutor`; the dashboard marks MCP-selected tabs runnable and skips CDP status checks for MCP starts.

## Active Blockers
- Supervised real Amex beta smoke still needs a tester present for login/MFA and explicit send/approval moments.
- Local macOS desktop artifacts are intentionally unsigned for the no-pay beta path.
- Desktop beta update checking and release verification are present; GitHub repo visibility is public. The app must describe updates as manual GitHub release downloads/replacements, not automatic in-place updates.
- Published `v1.0.1` is not update-checking capable because that release predates updater code/assets. `v1.0.2` is the first unsigned beta update-checking baseline.
- The currently running packaged app will not include the new Connect Existing Chrome, Auto-Connect Existing Chrome, or MCP-native run flows until the desktop app/helper are rebuilt and relaunched.
- MCP-native mode is intentionally minimal and not browser-use parity: keep action allowlist narrow and prefer local/mock verification before real authenticated customer-service actions.

## Immediate Next Step
If continuing implementation, run a source dashboard/manual smoke against a local mock page using **Auto-Connect Existing Chrome** and start a harmless MCP task from the UI. If preparing for beta, rebuild/repackage the desktop app/helper so the packaged app includes the MCP-native flow.

## Session State
- Last modified: 2026-07-06T04:16:16.703Z
- Verification passed: `pytest tests/unit/test_mcp_executor.py tests/unit/test_run_orchestration.py tests/unit/test_daemon_server.py -q` (30 passed), `node --check dashboard/dashboard.js`, `node --check scripts/test_helper_dashboard.mjs`, `node scripts/test_dashboard_protocol.mjs`, `npm run test:dashboard`, `pytest tests/unit -q` (132 passed), `ruff check src tests`, `git diff --check`.
- Live smoke: Chrome DevTools MCP `list_pages` returned 7 existing tabs; selected safe local CLIProxy tab; MCP executor ran `take_snapshot` then `report_outcome`; result `success`; artifact `/tmp/flyingpig-mcp-smoke/mcp_session_20260706_041301.json`.
- Files touched: AGENTS.md, CONTEXT.md, NOW.md, PLAN.md, src/agent/chrome_devtools_mcp.py, src/agent/mcp_executor.py, src/agent/brain.py, src/agent/run_orchestration.py, src/daemon/preflight.py, src/daemon/server.py, dashboard/index.html, dashboard/dashboard.js, dashboard/dashboard.css, tests/unit/test_chrome_devtools_mcp.py, tests/unit/test_mcp_executor.py, tests/unit/test_run_orchestration.py, tests/unit/test_daemon_server.py, tests/support/dashboard_daemon.py, scripts/test_helper_dashboard.mjs, plus pre-existing touched files from earlier source CDP attach work.
