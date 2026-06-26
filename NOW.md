# Now

## Current Focus
Public beta first-run readiness is implemented for the dashboard and docs: model/API-key setup is visible in the primary first-run flow, the dashboard explains the supervised work-window path, Start blocks unconfigured selected models, and local PII-free activation signals track onboarding milestones.

## Active Blockers
- Supervised real Amex beta smoke still needs a tester present for login/MFA and explicit send/approval moments.
- Local macOS desktop artifacts are intentionally unsigned for the no-pay beta path.
- Desktop beta update checking and release verification are present; GitHub repo visibility is public. The app must describe updates as manual GitHub release downloads/replacements, not automatic in-place updates.
- Published `v1.0.1` is not update-checking capable because it lacks updater code/assets. `v1.0.2` is the first unsigned beta update-checking baseline.

## Immediate Next Step
Review the first-run readiness diff, then decide whether to cut/publish the next unsigned beta release so public testers get the onboarding improvements.

## Session State
- Last modified: 2026-06-26T17:31:29.912Z
- Files touched: AGENTS.md, CONTEXT.md, NOW.md, PLAN.md, scripts/
