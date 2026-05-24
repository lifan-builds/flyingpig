<!-- context-harness:schema v2 -->

# Now

## Current Focus
Prepared Flying Pig 1.0.1 as the installable Mac desktop release, including the refreshed dashboard UI, automatic agent approach selection, dashboard model settings, Chinese release notes, screenshots, and rebuilt release artifacts.

## Active Blockers
- Supervised real Amex beta smoke still needs a tester present for login/MFA and explicit send/approval moments.
- macOS desktop artifact is unsigned because no local Developer ID identity is configured.
- `PRODUCT.md` and `DESIGN.md` are still absent, so the impeccable pass used `CONTEXT.md` and existing UI code as the design source of truth.

## Immediate Next Step
Push the release commit/tag and create the GitHub Release with the rebuilt source bundle and macOS desktop zip.

## Session State
- Last modified: 2026-05-24
- Files touched this session: `.env.example`, `AGENTS.md`, `CONTEXT.md`, `NOW.md`, `README.md`, `dashboard/index.html`, `dashboard/dashboard.js`, `dashboard/dashboard.css`, `desktop/status.css`, `docs/beta.md`, `docs/releases/v1.0.1-zh.md`, `docs/release-assets/v1.0.1/*.png`, `package.json`, `package-lock.json`, `pyproject.toml`, `scripts/build_beta_release.py`, `scripts/test_helper_dashboard.mjs`, `src/config.py`, `src/daemon/model_settings.py`, `src/daemon/server.py`, `tests/support/dashboard_daemon.py`, `tests/unit/test_config.py`.
- Verification: `ruff check src scripts tests`; `pytest tests -q -m "not slow"` (138 passed, 2 deselected); elevated `npm run test:dashboard` (helper_online=1828ms, work_window_ready=2052ms, mock_run_done=2199ms); elevated `npm run test:desktop`; `python scripts/build_beta_release.py`; `npm run build:helper`; `npm run desktop:package`; `git diff --check`; source and desktop release scans found no common secret/PII patterns or blocked filenames. Artifacts: `dist/flyingpig-beta-1.0.1.zip` SHA-256 `5f9e2cfc48933892513746ce04fc4e249a03ca8acb20811d8d41cb41a779c60b`; `dist/desktop/Flying Pig-1.0.1-arm64-mac.zip` SHA-256 `fef65229976165d5665782510a049a8ca44dc78a6d5eaafbe2bc0ed8f6159c48`.
