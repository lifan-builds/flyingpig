# Now

## Current Focus
Flying Pig 1.0.0 release prepared locally: source bundle, packaged helper, macOS desktop zip, release scans, and automated gates completed; next action is git push/tag publication.

## Active Blockers
- Supervised real Amex beta smoke still needs a tester present for login/MFA and explicit send/approval moments.
- macOS desktop artifact is unsigned because no local Developer ID identity is configured.

## Immediate Next Step
Push the release commit and `v1.0.0` tag to `origin/main`, then use the generated artifacts from `dist/` for release distribution.

## Session State
- Last modified: 2026-05-24
- Files touched this session: active release/version docs plus all staged desktop/dashboard/helper/runtime changes in the worktree.
- Verification: `ruff check src scripts tests`; `pytest tests -q -m "not slow"` (137 passed, 2 deselected); elevated `npm run test:dashboard`; elevated `npm run test:desktop`; `python scripts/build_beta_release.py`; `npm run build:helper`; `npm run desktop:package`; release zip scans passed.
