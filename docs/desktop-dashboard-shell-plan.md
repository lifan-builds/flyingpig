# Native Desktop Dashboard Shell Plan

## Summary

Build a cross-platform native desktop product shell for Flying Pig, but keep it as
a thin shell around the existing helper/dashboard architecture. The desktop app
replaces "run a script, then open localhost" with a normal app launch, while the
Python helper still owns browser-use, CDP, LLM calls, run state, and Controlled
Chrome launch.

Use Electron for v1 because the dashboard is already web-based, Electron gives a
stable bundled Chromium target, and it can supervise a helper sidecar quickly.
Reconsider Tauri later if app size becomes a real constraint.

## Approved Product Architecture

- Add a `desktop/` Electron app as the product entry point.
- Package the Python helper as a per-platform sidecar, likely via PyInstaller.
- Preserve the existing helper-served dashboard and WebSocket/API protocol.
- Keep browser-use, CDP launch policy, LLM calls, reconnectable run state,
  dashboard static hosting, and evidence/session behavior in the Python helper.
- Keep the Controlled Chrome Window separate from the desktop dashboard. The
  desktop app is the cockpit; the Chrome work window remains the browser-use
  work area.

## Desktop Shell Responsibilities

- Find an available localhost port for the helper.
- Start the helper sidecar, or the development helper in local dev.
- Wait for `/health` before loading the dashboard.
- Open a desktop dashboard window pointed at `/dashboard/`.
- Supervise helper process lifecycle and cleanly stop or detach it on app quit.
- Surface helper startup failures through a friendly recovery screen with retry
  and diagnostics.
- Own basic desktop integration such as app window behavior, native menus,
  notifications, logs path, and later auto-update.

## Product Behavior

- User double-clicks Flying Pig.
- The app opens the dashboard directly, with no terminal and no manual localhost
  URL.
- Dashboard shows helper/work-window status as it does today.
- User clicks Open Work Window; helper launches the dedicated Chrome profile.
- Decision Checkpoints, HUCA, cancel, reconnect, and result reporting continue
  through the existing helper/dashboard protocol.
- If helper startup fails, the desktop app shows a recovery screen with logs
  path, retry, and reset-work-profile actions.

## Packaging And Test Strategy

- Add packaging/build scripts for the Electron app and helper sidecar.
- Exclude recordings, secrets, cookies, logs, API keys, tokens, and
  user-specific account data from release artifacts.
- Unit-test helper launch command construction, port selection, and helper
  readiness behavior.
- Add an Electron smoke test: app starts, helper becomes healthy, dashboard
  loads.
- Extend existing dashboard smoke coverage so it can run against both direct
  helper URL and desktop shell when available.
- Manual acceptance: clean machine launch, Open Work Window, start mock run,
  Decision Checkpoint reload restore, HUCA restart, quit/reopen reconnect.

## Long-Running Agent Prompt

```markdown
You are working in `/Users/lfan/Project/flyingpig`.

Before doing anything, read `.trellis/workflow.md` and `.trellis/spec/flyingpig/index.md`, then follow the linked architecture, safety, and verification rules. Keep browser-use execution in the Python helper. Do not rewrite the dashboard or move browser automation into frontend JavaScript.

Goal: implement a high-quality cross-platform native desktop product shell for Flying Pig. The app should replace the current script/localhost startup experience with a normal desktop launch while preserving the existing helper-served dashboard, WebSocket/API protocol, Decision Checkpoints, HUCA, cancel/reconnect behavior, and separate Controlled Chrome Window.

Architecture direction:
- Add an Electron desktop app as the v1 native shell.
- Package the existing Python helper as a sidecar, likely via PyInstaller.
- Electron should own product startup, helper process supervision, window creation, retry/failure UX, and basic desktop integration.
- Python helper remains the owner of browser-use, CDP launch policy, LLM calls, run state, dashboard static hosting, and evidence/session behavior.
- The desktop dashboard window is the single cockpit. The Controlled Chrome Window remains the work area launched by the helper.

Implementation expectations:
1. Inspect the current helper entrypoints, dashboard assets, tests, and release scripts before editing.
2. Add a `desktop/` package with Electron main/preload/app configuration using the repo's existing JavaScript style.
3. Make Electron start the helper sidecar or development helper, wait for `/health`, then load `/dashboard/`.
4. Handle port conflicts by choosing or passing an available local port.
5. Add clean shutdown behavior that does not orphan helper processes in the normal app path.
6. Add a friendly helper startup failure screen or fallback state with retry and diagnostics.
7. Keep dashboard protocol changes minimal. If a helper endpoint is needed for diagnostics, add it narrowly and test it.
8. Add packaging/build scripts without including recordings, secrets, cookies, logs, API keys, tokens, or user-specific account data.
9. Preserve the existing beta helper path where useful for development, but make the desktop app the intended product entry point.
10. Update docs so users launch Flying Pig as an app, not by running `flyingpig-helper`.

Quality bar:
- Add focused unit tests for helper launch command construction, port selection, and helper readiness behavior.
- Add or extend smoke coverage so the dashboard still loads through the helper and the desktop shell can reach it.
- Keep existing checks passing: `ruff check src scripts tests`, `pytest tests -q -m "not slow"`, `node --check` for changed JS, and the dashboard smoke.
- If packaging cannot be fully completed in one pass, leave a working development desktop app plus a clear, tested packaging path.

Before finishing:
- Run the strongest practical verification.
- Record completed work and blockers in the active `.trellis/tasks/` artifact.
- Record durable project rules in `.trellis/spec/flyingpig/` and keep transient task state out of specs.
- If a durable architectural decision is made, add an ADR instead of burying it in chat.
```
