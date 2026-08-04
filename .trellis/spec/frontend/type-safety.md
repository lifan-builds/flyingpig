# JavaScript Runtime Contracts

## No Active TypeScript Layer

The active dashboard and desktop shell are plain JavaScript ES modules. There is no `tsconfig.json`, generated frontend type package, TypeScript compiler gate, Zod schema layer, or type-check command. Do not add TypeScript annotations, `any` guidance, or pretend `tsc` is part of validation. Python Pydantic models are authoritative at helper boundaries.

## Runtime Contract Pattern

- Keep pure protocol transformations explicit and exported from `dashboard/dashboard_protocol.js`. `checkpointOptionAnswer`, `checkpointCustomAnswer`, `fallbackPendingRequest`, `statusForPendingRequest`, and `progressMessage` convert one known shape to another and are covered by `scripts/test_dashboard_protocol.mjs`.
- Discriminate inbound WebSocket messages by `message.type` in `handleHelperMessage` before reading type-specific fields. Pending attention uses the allowlisted `userAttentionTypes` set and checkpoint `original_type`; malformed JSON is rejected by the `message` listener's parse boundary.
- Check uncertain collection/object shapes with `Array.isArray`, optional chaining, nullish defaults, `typeof`, and explicit fallback values before rendering. `renderTimingSpans`, `renderResultEvidence`, `loadActivationSignals`, and `compareBuildIdentity` are current examples.
- Build outbound objects in named serializers rather than spreading DOM or protocol objects wholesale. `runAuthorizationPayload`, `buildRunPayload`, checkpoint answer helpers, and `HelperSupervisor.diagnostics` intentionally expose bounded fields.
- Preserve wire names exactly. The dashboard uses helper protocol snake_case (`selected_message`, `authorized_actions`, `timing_spans`); build identity is the documented exception where desktop accepts `builtAt` and helper JSON uses `built_at`. See [Supervised MCP Runtime](../flyingpig/supervised-mcp-runtime.md).

## Authoritative Validation

REST request models in `src/daemon/server.py`, strict authorization models in `src/agent/run_authorization.py`, strict model actions in `src/agent/mcp_executor.py`, and reminder models in `src/daemon/follow_up_reminders.py` validate frontend input. Frontend checks improve UX but never replace helper validation, action allowlists, pre-flight, target resolution, checkpoint policy, or fresh-evidence completion.

Preserve each route's current response shape: operational routes commonly return `payload.ok` with `error`/`message`; run-state routes return snapshots; WebSocket failures use `type: "error"` and `text`. New copy must be fixed or safely categorized. Some `src/daemon/server.py` catch paths still place raw exception text in those fields, and `dashboard/dashboard.js` currently renders it; treat that end-to-end behavior as privacy debt to migrate, not a contract to copy or depend on.

## Electron IPC Isolation

`desktop/main.js` creates the window with `contextIsolation: true` and `nodeIntegration: false`. `desktop/preload.js` exposes a small `flyingPigDesktop` object through `contextBridge`, and `desktop/status.js` uses only that API. Keep IPC channel names and returned diagnostics explicit; never expose `ipcRenderer`, filesystem/process APIs, arbitrary invoke/send, command arguments, environment values, or log paths to the renderer.

## Protocol Tests as the Type Gate

Because there is no compile-time frontend type system, tests are the contract gate:

- `scripts/test_dashboard_protocol.mjs` asserts exact checkpoint serialization and status/attention mappings.
- `scripts/test_helper_dashboard.mjs` exercises helper REST/WebSocket shapes, per-target authorization UI, reconnectable checkpoints, progress, result, and follow-up rendering against synthetic services.
- `desktop/helper_supervisor.test.mjs` and `desktop/build_metadata.test.mjs` assert build/startup field names and privacy exclusions.
- Python tests such as `tests/unit/test_run_authorization.py` and `tests/unit/test_daemon_server.py` verify the authoritative side of the same wire contracts.

## Forbidden Patterns

- Trusting shape because a value came from the local helper, browser storage, page text, or Electron IPC.
- Generic serializers that forward unknown fields, aggregate authorization, or alter exact checkpoint messages.
- Dynamic `innerHTML`, `eval`, executable strings, or rendering raw private errors/log payloads.
- Weakening context isolation or enabling Node integration to bypass a missing bridge method.
- Inventing TypeScript, schema-generation, lint, or validation tooling and claiming it is an existing project gate.
