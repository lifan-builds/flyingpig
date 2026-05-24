# ADR 0004: Electron Native Desktop Shell

## Status

Accepted, 2026-05-20.

## Context

Flying Pig's beta helper-first flow still asks users to run or install a local
helper before opening a localhost dashboard. That is acceptable for development
but not for a consumer desktop product. The existing dashboard, WebSocket/API
protocol, Decision Checkpoints, HUCA, cancel/reconnect behavior, evidence
capture, and browser-use execution path are already owned by the Python helper
and should not be rewritten into frontend JavaScript.

## Decision

Use Electron for the v1 native desktop product shell.

Electron owns:

- product startup
- helper sidecar or development-helper process supervision
- helper port selection
- waiting for `/health`
- app window creation
- helper startup failure and retry UX
- clean helper shutdown in the normal app path
- packaging around a PyInstaller helper sidecar

The Python helper continues to own:

- browser-use execution
- CDP launch policy
- LLM calls
- run state
- dashboard static hosting
- WebSocket/API protocol
- evidence and session behavior

The desktop window is the single cockpit. The Controlled Chrome Window remains a
separate work area launched by the helper.

## Consequences

- The product can launch like a normal desktop app without asking users to open
  localhost manually.
- The dashboard protocol stays stable because Electron only passes the selected
  helper URL to the existing helper-served dashboard.
- The helper can still be run directly for development and service debugging.
- Release builds need two steps: build the PyInstaller helper sidecar, then
  package the Electron app with the sidecar as an extra resource.
- Every packaged artifact still needs a release privacy scan for PII, API keys,
  credentials, tokens, cookies, logs, recordings, and user-specific account
  data.
