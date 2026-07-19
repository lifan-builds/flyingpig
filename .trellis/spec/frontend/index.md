# Frontend Development Guidelines

The active frontend is the helper-served `dashboard/` plus the Electron shell in `desktop/`. Both use HTML, CSS, and plain JavaScript ES modules. There is no active React, Vue, Svelte, TypeScript, hook library, state library, or component library; React examples under `docs/legacy/` are historical only.

Start with the product-wide [Flying Pig specification](../flyingpig/index.md). The normal path is Electron -> packaged Python helper -> helper-served dashboard -> supervised Controlled Chrome/CDP/MCP runtime. Frontend code presents and transports helper-owned state; it does not own browser, model, authorization, completion, or evidence policy.

## Pre-Development Routing

1. Identify the surface: dashboard cockpit (`dashboard/`), desktop status/startup/update shell (`desktop/`), or a pure protocol helper/test (`dashboard/dashboard_protocol.js`, `scripts/`, `desktop/*.test.mjs`).
2. Read [Architecture](../flyingpig/architecture.md). For authorization, checkpoints, browser selection, progress, completion, stop/cancel, or startup diagnostics, also read [Safety and Authorization](../flyingpig/safety-auth.md), [Browser Runtime](../flyingpig/browser-runtime.md), and [Supervised MCP Runtime](../flyingpig/supervised-mcp-runtime.md).
3. For browser storage, API keys, diagnostics, notifications, result evidence, or local metrics, read [Data and Privacy](../flyingpig/data-privacy.md).
4. Choose the local guide below, then select safe checks from [Verification](../flyingpig/verification.md).

| Guide | Use it for |
|---|---|
| [Directory Structure](directory-structure.md) | Active file placement and dashboard/Electron ownership |
| [Imperative Views](component-guidelines.md) | Render functions, DOM construction, semantic HTML, and CSS |
| [Lifecycle and Async Work](hook-guidelines.md) | Events, fetch, WebSocket, timers, and page/process cleanup |
| [State Management](state-management.md) | Ephemeral state, local preferences, helper authority, checkpoints, and target scope |
| [JavaScript Runtime Contracts](type-safety.md) | Protocol discrimination, serializers, validation, and IPC isolation |
| [Quality](quality-guidelines.md) | Node tests, synthetic smokes, syntax, accessibility, and gated checks |

## Quality Check

- Changes remain plain ES modules unless an approved task explicitly changes the frontend stack; nothing imports the archived React path.
- Dashboard and desktop render helper-owned typed state without moving safety, browser, model, completion, or evidence policy into JavaScript.
- Dynamic content uses DOM nodes plus `textContent`/`replaceChildren`, not untrusted `innerHTML`; semantic controls remain keyboard-usable and labelled.
- WebSocket, event, timer, fetch, and Electron process lifecycles have an owner, cleanup, bounded waits, and visible failure behavior.
- Local storage is preference/input restoration only. Exact checkpoint messages and per-target authorization survive serialization without broadening.
- Electron keeps `contextIsolation: true`, `nodeIntegration: false`, and a narrow `contextBridge` API.
- Applicable pure Node tests, synthetic smokes, and `node --check` commands actually ran. GUI, live-browser, authenticated, packaging, signing, notarization, publishing, and release checks are reported as gated or skipped—not passed.
