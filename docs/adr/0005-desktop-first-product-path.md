# ADR 0005: Desktop-First Product Path

## Status

Accepted, 2026-05-21.

## Context

Flying Pig had accumulated multiple apparent entry points: the helper command,
the helper-served dashboard, the Electron desktop shell, the old Chrome
extension, and the old React frontend. The runtime architecture still needs a
Python helper and a web dashboard because browser-use execution, CDP launch
policy, LLM calls, run state, and evidence behavior must stay helper-owned.
But presenting every implementation layer as a product path makes testing,
documentation, support, and user onboarding too costly.

## Decision

Use the Electron desktop app as the only normal user-facing product path.

The Python helper remains an internal sidecar/runtime. The helper-served
dashboard remains the cockpit UI loaded by the desktop app. Direct
`flyingpig-helper`, `scripts/start.py`, `scripts/daemon.py`, and helper API
usage are development/debug paths only. The old Chrome extension and old React
frontend are archived under `docs/legacy/` for reference and are not active
product surfaces.

## Consequences

- Product docs and beta instructions describe one flow: open Flying Pig, launch
  the work window, start a supervised task.
- Desktop smoke tests cover the product entry point; dashboard smoke tests stay
  as fast protocol/UI regression tests.
- The helper can still be run directly for development, but it no longer opens
  a browser dashboard by default.
- Release artifacts should include the desktop shell, helper, helper-served
  dashboard, prompts, and tests/docs needed for the desktop product path, not
  legacy extension/frontend surfaces.
