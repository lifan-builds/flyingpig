# Now

## Current Focus
Helper-sidepanel prototype is archived; next work is the release architecture that makes the helper feel standalone without losing browser-use.

## Active Blockers
- Packaging choice still open: Chrome Native Messaging host vs. desktop helper/installer/autostart.

## Immediate Next Step
Draft and compare the packaged-helper options, then implement the smallest path that removes manual scripts while preserving the browser-use daemon.

## Session State
- Last modified: 2026-05-06T21:56:09-07:00
- Files touched: CONTEXT.md, PLAN.md, NOW.md
- Archive: `c19ec69` pushed to `https://github.com/lifan-builds/flyingpig`
- Verification: prior helper-sidepanel checks passed (`pytest tests/unit/test_daemon_server.py`, `npm run test:extension`, focused lint/compile). This context update is docs-only.
