# Verification

Choose checks for the changed surface and report each result honestly. A skipped live or release probe is not a pass.

## Default Safe Gates

```bash
python3 -m ruff check src scripts tests
python3 -m pytest tests/unit -q -p no:cacheprovider
python3 -m pytest tests -q -m "not slow" -p no:cacheprovider
npm run test:dashboard
npm run test:desktop
node --check dashboard/dashboard.js
node --check scripts/test_dashboard_protocol.mjs
node --check scripts/test_helper_dashboard.mjs
git diff --check
```

Add focused tests for changed modules and syntax-check every changed or retained JavaScript entry point. Ruff is configured for Python 3.12 and a 100-column limit. Mypy is an optional dependency but has no repository command/configuration, so do not invent it as a mandatory gate.

## Trellis and Configuration Gates

```bash
python3 ./.trellis/scripts/get_context.py
python3 ./.trellis/scripts/get_context.py --mode phase
python3 ./.trellis/scripts/get_context.py --mode packages
python3 ./.trellis/scripts/task.py current --source
python3 ./.trellis/scripts/task.py list
```

- Require the `flyingpig` spec layer and its checklist to be discoverable.
- Parse changed JSON, TOML, and YAML with appropriate parsers.
- Verify Claude and Codex hook targets resolve to repository-local Trellis files.
- Verify generated platform surfaces are limited to `.claude/`, `.codex/`, and required shared `.agents/` plus Trellis core.
- Test task lifecycle only with a uniquely named disposable task in an isolated worktree; never mutate real work as a fixture.

## Gated Checks

- Tests marked `slow`, real/e2e browser sessions, and authenticated customer-service actions may launch browsers, require login/MFA, or affect external state. Run only when the changed surface justifies them and a user is present/has authorized the action.
- `npm run desktop:dev`, helper/package builds, `desktop:package`, signing checks, notarization, and GitHub release verification may launch processes or create large artifacts. Run them only for affected release/build surfaces and isolate generated output.
- Never run `npm run desktop:publish` as a routine check.
- Never send a live chat message, accept an offer, cancel an account, or perform HUCA merely to validate code.

## Sensitive Review

Inspect all changed/untracked/staged names and relevant content. Confirm that `.env`, browser state, recordings, local DBs, account/chat data, dependency/build output, signing material, and release artifacts are absent. Scan tracked examples and fixtures for credentials and private data without reading ignored secret values.
