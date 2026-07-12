# Now

## Current Focus
Simplified the desktop dashboard into a configure-once, state-driven assistant while preserving supervised runs, authorization, browser, evidence, reminder, and recovery controls.

## Active Blockers
- Supervised real Amex beta smoke still needs a tester present for login/MFA and explicit send/approval moments.
- Local macOS desktop artifacts are intentionally unsigned for the no-pay beta path.
- Desktop beta update checking and release verification are present; GitHub repo visibility is public. The app must describe updates as manual GitHub release downloads/replacements, not automatic in-place updates.
- Published `v1.0.1` is not update-checking capable because that release predates updater code/assets. `v1.0.2` is the first unsigned beta update-checking baseline.
- The currently running packaged app will not include the new Connect Existing Chrome, Auto-Connect Existing Chrome, or MCP-native run flows until the desktop app/helper are rebuilt and relaunched.
- MCP-native mode is intentionally minimal and not browser-use parity: keep action allowlist narrow and prefer local/mock verification before real authenticated customer-service actions.

## Immediate Next Step
Rebuild and relaunch the desktop app/helper, then visually confirm the simplified configured-user dashboard in the packaged Electron shell before the next supervised real Amex run.

## Session State
- Last modified: 2026-07-12 America/Los_Angeles
- Live Amex outcome: a Membership Consulting representative confirmed the requested account was invalidated and submitted for cancellation. A confirmation email is expected within 24-48 hours. After any credit posts, the user must contact Amex again to request transfer to a bank account or a check.
- Runtime fixes: structured run authorization; transcript-derived workflow and completion state; transactional verified chat sending; duplicate suppression; active-human patience; bounded/fallback MCP planning; trailing-JSON recovery; textless waits; CLIProxy list/probe routing; freshest transcript evidence; deferred follow-up metadata.
- Dashboard fixes: explicit target/action/refund/HUCA authorization controls, conservative payload construction, completion checklist, confirmation expectation, follow-up rendering, reminder scheduling, and due notifications.
- Reminder runtime: helper-owned atomic JSON persistence, create/list/cancel APIs, reconnect-safe due claiming, and WebSocket delivery from `src/daemon/follow_up_reminders.py`.
- Verification passed: `pytest tests/unit -q` (154 passed), `ruff check src tests`, JavaScript syntax checks, `npm run test:dashboard`, `npm run build:helper`, `npm run desktop:package`, `npm run desktop:verify-update`, release path/content scans, and `git diff --check`.
- Dashboard simplification verification: configured model setup collapses and reopens through Settings, secondary run controls stay under Run options, and the 390px dashboard smoke has no horizontal overflow.
- Focused workflow verification: Start automatically opens the work window when needed; request, preparation, running, attention, and result states replace one another; activity remains hidden until requested.
- First-use guidance: Configure, Open website, and Start now render as three sequential screens; repeat users skip directly to the request form, and invalid saved model configuration fully returns to Step 1.
- Packaged artifact: `dist/desktop/Flying-Pig-1.0.2-arm64-mac.zip`, SHA-256 `4dfbc7313e73fdd2ff01904ed8b3580efadb58e819ba2206ff5b27d0008943ac` (intentionally unsigned).
- Files touched for this design task: `PRODUCT.md`, `DESIGN.md`, dashboard files, dashboard smoke support, `PLAN.md`, `CONTEXT.md`, and `NOW.md`. Existing coherent backend and context-harness changes remain included and were not reverted.
