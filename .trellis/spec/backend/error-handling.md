# Backend Error Handling

## Validate at Boundaries

- Let Pydantic reject malformed REST request bodies in `src/daemon/server.py`. Use strict models (`ConfigDict(extra="forbid")`) for security-sensitive model/tool data as shown by `AuthorizationTarget`, `RunAuthorization`, and `McpAgentAction`.
- Return structured pre-flight failures from `preflight_check()` in `src/daemon/preflight.py`; do not replace helper policy with frontend validation.
- Treat page text, chat text, MCP payloads, and model output as untrusted. Parse once, validate schemas/allowlists, and keep recovery bounded as specified by [Safety and Authorization](../flyingpig/safety-auth.md) and [Supervised MCP Runtime](../flyingpig/supervised-mcp-runtime.md).

## Internal Exceptions and Async Lifecycle

Use narrow exceptions when callers need a stable category. `McpPhaseError` in `src/agent/mcp_executor.py` carries only `phase` and a payload-free `category`; `_run_phase()` maps timeout, cancellation, and other failures while emitting terminal progress/timing.

Async owners must preserve lifecycle semantics:

- re-raise `asyncio.CancelledError` after cleanup/state publication;
- bound blocking phases with `asyncio.wait_for` and move synchronous bridges through `asyncio.to_thread`;
- cancel and gather observer tasks during teardown;
- keep graceful supervisor stop distinct from hard cancellation (`RunManager.stop`, `RunManager.cancel`, and `_cancel_active_run` in `src/daemon/server.py`).

Do not use broad `except Exception: pass`. Best-effort local reads may fall back safely—`FollowUpReminderStore._load` returns an empty list for unreadable local JSON—but execution failures need a safe state, diagnostic log, and actionable public response.

## Current Public Error Shapes

Preserve the client contract for the route being changed:

- Operational REST endpoints return JSON with `{"ok": false, "error": "actionable message"}` (for example model settings, browser launch/attach, MCP connect/select, and run outcome in `src/daemon/server.py`). Run-state endpoints return the reconnectable state snapshot; pre-flight denial is also broadcast as `type="preflight_failed"` with structured `failures`.
- WebSocket command errors use `{"type": "error", "text": "actionable message"}`. User-attention, pre-flight, progress, timing, result, and state messages remain distinct typed messages rather than being collapsed into exceptions.
- FastAPI/Pydantic may return its normal HTTP validation response for malformed request bodies. Do not invent a second envelope unless all clients/tests are migrated together.

For new runtime failures, expose a fixed safe category and fixed/actionable copy, not raw prompts, snapshots, tool arguments/results, chat content, authorization target values, credentials, private URLs, commands, environment values, or user paths. The allowlisted MCP categories and error matrix are defined in [Supervised MCP Runtime](../flyingpig/supervised-mcp-runtime.md). Some older catch blocks still stringify exception type/message in `src/daemon/server.py`; treat those as privacy-review hotspots, not a pattern to expand.

## Logging Versus User Responses

Log the failing phase with `logger.exception(...)` when a traceback is useful, then send a scrubbed public response with fixed copy or a safe category. `McpBrowserExecutor._safe_error_category` is the representative category boundary. The `browser_launch` and agent-run handlers in `src/daemon/server.py` currently log locally but then stringify raw exceptions publicly; they are privacy-review hotspots to migrate, not examples to copy. See [Logging](logging-guidelines.md) for exclusions.

## Common Mistakes

- Exposing raw private exceptions or log payloads to REST, WebSocket, dashboard, or desktop startup UI.
- Catching cancellation as an ordinary failure or storing graceful stop as bare `cancelled`.
- Retrying indefinitely, omitting a timeout, or blocking the event loop during recovery.
- Returning `{ok: false}` but also mutating external/browser state after the reported failure.
- Letting transport handlers infer authorization, completion, checkpoint, or browser policy.
- Converting exact approved checkpoint messages to summaries before they reach verified send.
