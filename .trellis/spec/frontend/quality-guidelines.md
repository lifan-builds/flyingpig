# Frontend Quality Guidelines

## Baseline Safe Gates

Select applicable commands from [Verification](../flyingpig/verification.md). For normal dashboard/desktop changes, the existing gates are:

```bash
npm run test:dashboard
npm run test:desktop
node --check dashboard/dashboard.js
node --check dashboard/dashboard_protocol.js
node --check desktop/main.js
node --check desktop/preload.js
git diff --check
```

Syntax-check every changed JavaScript entry point, not only the examples above. The repository has no ESLint, Prettier, TypeScript, browser-coverage, or frontend build gate; do not invent one or report it passed.

## Existing Test Layers

- `scripts/test_dashboard_protocol.mjs` is a pure Node assertion suite for protocol formatting, attention classification, status mapping, and exact checkpoint answers.
- `desktop/*.test.mjs` use `node:test` with fakes and temporary directories for helper supervision, build metadata, and update behavior. `desktop/helper_supervisor.test.mjs` asserts safe diagnostics omit command, args, and log path.
- `scripts/test_helper_dashboard.mjs` launches synthetic local helper/site fixtures and a temporary headless Puppeteer profile. It checks first-run sequencing, storage migration, responsive layout, work-window/MCP selection, per-target authorization, progress/results, reminders, local metrics, HUCA, stop, and checkpoint reconnect.
- `scripts/test_desktop_shell.mjs` is the local desktop-shell/helper dashboard smoke. It starts only `tests.support.dashboard_daemon` and verifies the served cockpit; it does not prove the Electron GUI, packaged helper, or live Chrome.
- Cross-layer Python tests such as `tests/unit/test_daemon_server.py`, `tests/unit/test_run_authorization.py`, and `tests/unit/test_mcp_executor.py` remain required when a frontend change alters helper protocol or safety semantics.

Use localhost, temporary profiles/directories, fake IPC/processes, and unmistakably synthetic values. Never use real accounts, chats, keys, browser profiles, or customer-service actions as fixtures.

## Review Checklist

- Product ownership remains Electron shell -> helper -> dashboard -> Controlled Chrome; no framework or legacy product path was revived.
- DOM rendering uses semantic nodes and `textContent`/`replaceChildren`; no untrusted `innerHTML`, raw error/log payload, private URL, target/account detail, credential, command/env value, or user path leaks into diagnostics.
- Async operations restore busy state; sockets/listeners/timers/process waits have an owner, bounded behavior, cleanup, and safe visible failure.
- REST/WebSocket message names and fields match Python; reconnect snapshots, pending attention, progress, completion, and stop/cancel states render without frontend policy inference.
- Checkpoint `message_to_send` is displayed and returned exactly. Structured target rows retain separate action lists; aggregate controls never broaden authorization.
- Electron still uses `contextIsolation: true`, `nodeIntegration: false`, and the narrow preload bridge.
- Local storage contains only convenience preferences/drafts and coarse local metrics, never secrets or authoritative run state.

## Accessibility and Responsive Review

Preserve semantic landmarks, native buttons/forms, labels, fieldsets/legends, `aria-live`, `aria-expanded`, visible focus, text status alongside color, and narrow-layout behavior in `dashboard/index.html`/`dashboard.css` and `desktop/status.html`/`status.css`. Run the Puppeteer narrow-layout assertions when dashboard structure changes and manually reason through keyboard order for new controls.

Known gap: there is no automated axe, screen-reader, full keyboard-navigation, or accessibility-lint suite, and some dynamically generated labels need stronger `for`/`id` linkage. State this honestly; passing the current smoke is not proof of full accessibility compliance.

## Forbidden and Gated Work

Do not add dynamic `innerHTML`, move helper policy into UI/Electron, trust local storage, weaken renderer isolation, block the renderer, auto-retry consequential sends, revive archived React/extension code, or introduce frameworks/tooling/infrastructure outside approved scope.

`npm run desktop:dev`, headed GUI checks, real Controlled Chrome/MCP sessions, authenticated customer-service runs, helper/package builds, signing, notarization, GitHub release verification, and update replacement are separately gated. `npm run desktop:publish` is never routine validation. Report each gated/skipped check as gated/skipped; never claim it passed because a local Node or synthetic smoke passed.
