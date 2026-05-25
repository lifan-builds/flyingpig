<!-- context-harness:schema v2 -->

# Now

## Current Focus
Assessing broader-audience beta readiness after the no-pay unsigned Mac release path, with emphasis on reducing first-run configuration friction, explaining the supervised workflow, and improving first-success measurement.

## Active Blockers
- Supervised real Amex beta smoke still needs a tester present for login/MFA and explicit send/approval moments.
- Local macOS desktop artifacts are intentionally unsigned for the no-pay beta path.
- `PRODUCT.md` is still absent. `DESIGN.md` now exists and uses `CONTEXT.md` plus current UI code as the product/design source of truth.
- Desktop beta update checking and release verification are present; GitHub repo visibility is public. The app must describe updates as manual GitHub release downloads/replacements, not automatic in-place updates.
- Published `v1.0.1` is not update-checking capable because it lacks updater code/assets. `v1.0.2` should be the first unsigned beta update-checking baseline.
- Current Mac still has no local `Developer ID Application` identity, and the GitHub repo lacks signing/notarization secrets. This is acceptable for the no-pay unsigned beta path.

## Immediate Next Step
Prioritize a first-run setup/onboarding pass: make model/API-key setup obvious outside Advanced, add a short in-app how-to path for the supervised work-window flow, and define the first-run success signals before wider Reddit/forum promotion.

## Session State
- Last modified: 2026-05-25
- Files touched this session: `CONTEXT.md`, `PLAN.md`, `NOW.md`, `src/agent/evidence.py`, `src/daemon/server.py`, `dashboard/index.html`, `dashboard/dashboard.js`, `dashboard/dashboard.css`, `desktop/auto_update.js`, `desktop/auto_update.test.mjs`, `desktop/main.js`, `desktop/preload.js`, `desktop/electron-builder.json`, `docs/desktop-auto-update.md`, `package.json`, `package-lock.json`, `scripts/test_helper_dashboard.mjs`, `tests/unit/test_daemon_run_session.py`, `tests/unit/test_daemon_server.py`.
- Additional files touched for update hardening: `.github/workflows/desktop-release.yml`, `desktop/entitlements.mac.plist`, `desktop/entitlements.mac.inherit.plist`, `scripts/verify_desktop_update_release.mjs`, `pyproject.toml`, `scripts/build_beta_release.py`, `src/api/main.py`.
- Additional files touched for signing setup: `docs/desktop-auto-update.md`, `package.json`, `scripts/check_macos_signing_setup.mjs`.
- Additional files touched for no-pay beta update path: `.github/workflows/desktop-release.yml`, `CONTEXT.md`, `desktop/auto_update.js`, `desktop/auto_update.test.mjs`, `desktop/electron-builder.json`, `desktop/main.js`, `docs/desktop-auto-update.md`.
- Additional release-gate fix: `pyproject.toml` now declares `aiosqlite`, which `src/models/db.py` needs for the default `sqlite+aiosqlite` test/dev database URL.
- Additional CI timing fix: `tests/unit/test_daemon_server.py` gives the REST decision-checkpoint completion poll a longer window after answering because GitHub Actions was slower than the old one-second budget.
- Verification: `ruff check src scripts tests`; `pytest tests -q -m "not slow"` (139 passed, 2 deselected); `node --test desktop/auto_update.test.mjs`; `node scripts/test_dashboard_protocol.mjs`; elevated `npm run test:desktop`; elevated `npm run test:dashboard` (`helper_online=2286ms`, `work_window_ready=2509ms`, `mock_run_done=2657ms`); `npm run desktop:package`; `npm run desktop:verify-update`; `npm run desktop:verify-update -- --require-signed` failed as expected because no local Developer ID identity exists; `npm run desktop:verify-update -- --github --tag=v1.0.1` failed as expected because the old release lacks update assets. Packaging emitted `dist/desktop/latest-mac.yml` and `Flying-Pig-1.0.2-arm64-mac.zip`, still unsigned locally.
- Signing setup verification: `node --check scripts/check_macos_signing_setup.mjs`; `npm run desktop:check-signing` failed as expected because no local Developer ID identity or local signing env vars exist; elevated `npm run desktop:check-signing -- --github` confirmed the GitHub repository currently lacks `MAC_CSC_LINK`, `MAC_CSC_KEY_PASSWORD`, `APPLE_API_KEY_P8`, `APPLE_API_KEY_ID`, `APPLE_API_ISSUER`, and `APPLE_TEAM_ID`.
- No-pay beta update verification: `node --check desktop/auto_update.js`; `node --check desktop/main.js`; `node --test desktop/auto_update.test.mjs` (4 passed); elevated `npm run test:desktop` (8 passed plus shell smoke); `npm run desktop:package` succeeded and Electron Builder reported `skipped macOS code signing reason=identity explicitly is set to null`; `npm run desktop:verify-update` passed while warning that codesign failed because `--require-signed` was not set.
- GitHub Actions release attempt `26382941970` failed in `Verify code before release` because CI installed from `pyproject.toml` and `aiosqlite` was missing. Attempt `26383021474` got past dependency install but failed a timing-sensitive REST checkpoint test. After fixes, local release-gate checks pass: `ruff check src scripts tests`; `pytest tests/unit/test_daemon_server.py::test_rest_run_endpoints_answer_pending_decision_checkpoint -q`; `pytest tests -q -m "not slow"` (139 passed, 2 deselected); elevated `npm run test:desktop`.
- GitHub Actions release attempt `26383115586` succeeded for `v1.0.2`. Published release: `https://github.com/lifan-builds/flyingpig/releases/tag/v1.0.2` with `Flying-Pig-1.0.2-arm64-mac.zip`, `.zip.blockmap`, and `latest-mac.yml`. Elevated `npm run desktop:verify-update -- --github --tag=v1.0.2` passed, warning only that the local package is unsigned because `--require-signed` was not set.
