# Now

## Current Focus
Beta release artifact: package the helper service plus side-panel extension into something a first-cohort user can install.

## Active Blockers
- Local beta bundle exists; remaining blocker is a real supervised Amex smoke, which requires the user's Amex login/MFA and explicit send confirmation.

## Immediate Next Step
Run a supervised Amex beta smoke from the side panel with the user present, then review the transcript before first-cohort rollout.

## Session State
- Last modified: 2026-05-07T00:00:00-07:00
- Files touched: src/helper.py, src/helper_service.py, src/daemon/server.py, pyproject.toml, README.md, docs/beta.md, extension/, tests/, PLAN.md, NOW.md
- Archive: `c19ec69` pushed to `https://github.com/lifan-builds/flyingpig`
- Verification: `ruff check src scripts tests`, `pytest tests -q -m "not slow"`, `python -m src.helper --help`, `python -m src.helper_service --help`, `python -m src.helper_service status`, `python scripts/build_beta_release.py --clean`, elevated `npm run test:extension`, LaunchAgent install, and elevated localhost `/health` check passed.
