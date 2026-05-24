# Now

## Current Focus
Flying Pig 1.0.0 release is committed, tagged, and pushed to `origin/main`; local source and macOS desktop artifacts are built under `dist/`.

## Active Blockers
- Supervised real Amex beta smoke still needs a tester present for login/MFA and explicit send/approval moments.
- macOS desktop artifact is unsigned because no local Developer ID identity is configured.

## Immediate Next Step
Use `dist/flyingpig-beta-1.0.0.zip` and `dist/desktop/Flying Pig-1.0.0-arm64-mac.zip` for release distribution, or create a GitHub release from tag `v1.0.0`.

## Session State
- Last modified: 2026-05-24
- Files touched this session: active release/version docs plus all staged desktop/dashboard/helper/runtime changes in the worktree.
- Verification: `ruff check src scripts tests`; `pytest tests -q -m "not slow"` (137 passed, 2 deselected); elevated `npm run test:dashboard`; elevated `npm run test:desktop`; `python scripts/build_beta_release.py`; `npm run build:helper`; `npm run desktop:package`; release zip scans passed; pushed commit `ed8cec6` and tag `v1.0.0`.
