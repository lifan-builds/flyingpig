# Frontend Directory Structure

## Active Product Boundary

The frontend is not under `src/`. The active user path is Electron -> packaged Python helper -> helper-served dashboard. See [Architecture](../flyingpig/architecture.md) for cross-layer ownership.

```text
dashboard/
├── index.html                 # cockpit landmarks and stable element IDs
├── dashboard.css             # cockpit layout, states, controls, responsive rules
├── dashboard.js              # imperative views, events, REST/WebSocket client
├── dashboard_protocol.js     # pure protocol formatting/serialization helpers
├── setup.html                # development setup fallback page
└── assets/                   # dashboard icons

desktop/
├── main.js                    # BrowserWindow, IPC handlers, helper/update supervision
├── preload.js                # narrow contextBridge API
├── status.html|status.js|status.css
├── helper_supervisor.js      # helper process/health/startup contract
├── auto_update.js            # desktop update behavior
├── *.test.mjs                # pure Node desktop tests
├── electron-builder.json     # packaging configuration
└── pyinstaller/              # packaged helper specification
scripts/
├── test_dashboard_protocol.mjs
├── test_helper_dashboard.mjs
└── test_desktop_shell.mjs
```

`docs/legacy/` contains archived React/extension material. It is not a source directory for current features.

## Placement Rules

- Keep stable page structure and labels in `dashboard/index.html`; keep state-dependent rendering and listeners in focused functions in `dashboard/dashboard.js` such as `updateWorkflowView`, `renderDecisionCheckpoint`, and `renderResultEvidence`.
- Put protocol logic that can run without a DOM in `dashboard/dashboard_protocol.js`. `checkpointOptionAnswer`, `statusForPendingRequest`, and `progressMessage` are tested directly by `scripts/test_dashboard_protocol.mjs`.
- Keep dashboard styling in `dashboard/dashboard.css`. Desktop startup UI has its own `desktop/status.*` files so helper-start failures do not depend on the dashboard loading.
- Put Electron lifecycle, windows, and IPC registration in `desktop/main.js`; expose only narrow renderer capabilities from `desktop/preload.js`; keep process/port/health logic independently testable in `desktop/helper_supervisor.js`.
- Add tests at the seam they exercise: pure dashboard protocol checks in `scripts/test_dashboard_protocol.mjs`, synthetic DOM/protocol smoke in `scripts/test_helper_dashboard.mjs`, desktop module tests in `desktop/*.test.mjs`, and the local shell/helper smoke in `scripts/test_desktop_shell.mjs`.

## Naming and Imports

Use lowercase descriptive `.js`, `.html`, and `.css` filenames; `camelCase` functions/variables; and `UPPER_SNAKE_CASE` only for genuine constants. Keep relative `.js` extensions in ES-module imports. Stable DOM IDs are `camelCase`; reusable CSS classes are lowercase kebab-case. Test files use `.test.mjs` for `node --test`, while executable smoke scripts use `test_*.mjs`.

## Common Mistakes

- Do not create `src/components`, `src/hooks`, a TypeScript tree, a bundler, or a frontend framework to implement a small dashboard change.
- Do not revive `docs/legacy/`, the old extension, or a localhost-first developer UI as a normal product path.
- Do not place helper safety, authorization, completion, browser, model, evidence, or persistence policy in `dashboard/` or `desktop/`.
- Do not turn `dashboard/dashboard.js` into a second protocol implementation when pure transformations belong in `dashboard_protocol.js` or authoritative validation belongs in Python.
- Do not weaken the `desktop/main.js` / `desktop/preload.js` renderer-isolation boundary for convenience.
