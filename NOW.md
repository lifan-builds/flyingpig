<!-- context-harness:schema v2 -->

# Now

## Current Focus
Hardened desktop auto-update release operations and prepared `v1.0.2` as the first update-capable baseline.

## Active Blockers
- Supervised real Amex beta smoke still needs a tester present for login/MFA and explicit send/approval moments.
- Local macOS desktop artifacts are unsigned because this machine has no valid Developer ID identity.
- `PRODUCT.md` is still absent. `DESIGN.md` now exists and uses `CONTEXT.md` plus current UI code as the product/design source of truth.
- Desktop auto-update plumbing and release verification are present; GitHub repo visibility is public, but a successful user-facing update release still requires Developer ID/App Store Connect secrets in GitHub Actions or a local signing identity.
- Published `v1.0.1` is not update-capable because it lacks updater code/assets. `v1.0.2` should be the first signed/notarized baseline.

## Immediate Next Step
Add the required GitHub repository secrets for signing/notarization, run the `Desktop Release` workflow for `v1.0.2`, then verify an installed `v1.0.2` can update to a later test release.

## Session State
- Last modified: 2026-05-25
- Files touched this session: `CONTEXT.md`, `PLAN.md`, `NOW.md`, `src/agent/evidence.py`, `src/daemon/server.py`, `dashboard/index.html`, `dashboard/dashboard.js`, `dashboard/dashboard.css`, `desktop/auto_update.js`, `desktop/auto_update.test.mjs`, `desktop/main.js`, `desktop/preload.js`, `desktop/electron-builder.json`, `docs/desktop-auto-update.md`, `package.json`, `package-lock.json`, `scripts/test_helper_dashboard.mjs`, `tests/unit/test_daemon_run_session.py`, `tests/unit/test_daemon_server.py`.
- Additional files touched for update hardening: `.github/workflows/desktop-release.yml`, `desktop/entitlements.mac.plist`, `desktop/entitlements.mac.inherit.plist`, `scripts/verify_desktop_update_release.mjs`, `pyproject.toml`, `scripts/build_beta_release.py`, `src/api/main.py`.
- Verification: `ruff check src scripts tests`; `pytest tests -q -m "not slow"` (139 passed, 2 deselected); `node --test desktop/auto_update.test.mjs`; `node scripts/test_dashboard_protocol.mjs`; elevated `npm run test:desktop`; elevated `npm run test:dashboard` (`helper_online=2286ms`, `work_window_ready=2509ms`, `mock_run_done=2657ms`); `npm run desktop:package`; `npm run desktop:verify-update`; `npm run desktop:verify-update -- --require-signed` failed as expected because no local Developer ID identity exists; `npm run desktop:verify-update -- --github --tag=v1.0.1` failed as expected because the old release lacks update assets. Packaging emitted `dist/desktop/latest-mac.yml` and `Flying-Pig-1.0.2-arm64-mac.zip`, still unsigned locally.
