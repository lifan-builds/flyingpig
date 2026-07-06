# Now

## Current Focus
Implemented and minimally live-smoked Flying Pig's Claude-Code-style **Auto-Connect Existing Chrome** path through a helper-owned Chrome DevTools MCP bridge. The helper starts `npx -y chrome-devtools-mcp@latest --autoConnect`, lists existing user Chrome tabs, selects a user-chosen tab, and verifies control with `take_snapshot`. The smoke test confirmed MCP can see/control the existing Chrome session and snapshot a safe localhost tab.

## Active Blockers
- Supervised real Amex beta smoke still needs a tester present for login/MFA and explicit send/approval moments.
- Local macOS desktop artifacts are intentionally unsigned for the no-pay beta path.
- Desktop beta update checking and release verification are present; GitHub repo visibility is public. The app must describe updates as manual GitHub release downloads/replacements, not automatic in-place updates.
- Published `v1.0.1` is not update-checking capable because that release predates updater code/assets. `v1.0.2` is the first unsigned beta update-checking baseline.
- The currently running packaged app will not include the new Connect Existing Chrome or Auto-Connect Existing Chrome flows until the desktop app/helper are rebuilt and relaunched.
- The real MCP smoke did not expose a browser-use-compatible CDP handoff URL. MCP control works for listing/selecting/snapshotting existing Chrome tabs, but browser-use execution still needs either an explicit CDP endpoint or a future MCP-native browser backend.

## Immediate Next Step
If the goal is full agent execution inside the existing normal Chrome tab without a CDP URL, implement an MCP-native browser backend or adapter for the subset of browser-use actions Flying Pig needs. If the goal is the current staged UI, rebuild/repackage or run the source helper/app and verify **Auto-Connect Existing Chrome** from the dashboard.

## Session State
- Last modified: 2026-07-05T19:35:00 local
- Live smoke: `list_pages` returned 6 existing Chrome tabs; selecting a safe localhost tab succeeded; `take_snapshot` returned `snapshot_available:true`; `browser_ready:false` because no CDP handoff URL was exposed.
- Files touched: AGENTS.md, CONTEXT.md, NOW.md, PLAN.md, src/agent/chrome_devtools_mcp.py, src/daemon/server.py, dashboard/index.html, dashboard/dashboard.js, dashboard/dashboard.css, tests/unit/test_chrome_devtools_mcp.py, tests/unit/test_daemon_server.py, tests/support/dashboard_daemon.py, scripts/test_helper_dashboard.mjs, plus pre-existing touched files from earlier source CDP attach work.
