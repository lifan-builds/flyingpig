# Frontend Lifecycle and Async Guidelines

## Framework Hooks Are Not Applicable

There are no React/Vue/Svelte hooks in the active frontend. Stateful behavior uses browser/Electron lifecycle events, async functions, WebSocket handlers, and explicitly owned timers. Do not introduce `use*` abstractions or a data-fetching library unless an approved task changes the stack.

## Page and Event Lifecycle

- Register the dashboard's stable listeners once inside the `DOMContentLoaded` initializer in `dashboard/dashboard.js`, after `loadSettings`, `loadActivationSignals`, and the initial tab refresh establish state.
- Bind listeners for dynamic nodes when constructing them. `renderMcpPages`, `addAuthorizationTargetRow`, `renderResultEvidence`, and `renderDecisionCheckpoint` are examples.
- Keep event handlers thin: read/normalize control values, call one operation, then route rendering through shared update functions. Protocol transformation belongs in `dashboard_protocol.js`; helper policy remains Python-owned.
- Desktop renderer actions go through `window.flyingPigDesktop`, the narrow bridge exposed by `desktop/preload.js`. Electron lifecycle and IPC ownership stay in `desktop/main.js`.

## Fetch and WebSocket Work

- Use `async`/`await` and handle failure at the operation boundary. Browser/model/reminder methods in `dashboard/dashboard.js` set visible status and use `try`/`catch`; operations with a busy flag restore it in `finally`.
- Decode JSON, check both HTTP status where relevant and the route's existing `payload.ok` contract, then render only expected fields. Never display raw helper logs, command/env data, or unbounded exception payloads.
- `connectHelper` owns one WebSocket. Its `open`, `close`, `error`, and `message` listeners update connection state; `handleHelperMessage` discriminates typed messages. Reconnect explicitly closes and replaces the prior socket.
- Reconnect must accept the helper's `state` snapshot and pending request as authoritative. Do not replay a dashboard-only run or synthesize completion after a disconnect.

## Timer and Process Ownership

Own each repeating timer in state and clear it on every terminal/replacement path. The current browser poll follows this shape:

```javascript
if (state.browserStatusTimer) clearInterval(state.browserStatusTimer);
state.browserStatusTimer = setInterval(refreshBrowserStatus, 5000);
```

`connectHelper` clears that timer on both WebSocket close and error. `HelperSupervisor.stop` in `desktop/helper_supervisor.js` similarly owns and clears its force-kill timeout. Python owns daemon reminder polling and run observers; do not duplicate those loops in the UI.

Use bounded waits and explicit terminal UI for startup/polling. `waitForHelperReady` has a deadline and per-request timeout; `HelperSupervisor.start` races health against spawn failure/early exit. Never add an unbounded reconnect, health, or action loop.

## Cleanup and Common Mistakes

- Clean up intervals, sockets, listeners, and pending process waits when their owner is replaced or destroyed. A new preload subscription API should return an unsubscribe function; the current `onStatus`/`onUpdateStatus` bridge does not, so do not multiply subscriptions.
- Do not block the renderer with synchronous process, filesystem, CDP, or MCP work. Electron main/process supervision and Python helper APIs own those operations.
- Do not fire consequential requests from rendering functions, retry a send automatically, or let close/error handlers erase helper-authoritative result state.
- Do not catch and silently claim success. Show safe fallback copy and leave the control retryable; report gated live behavior as untested when it was not exercised.
