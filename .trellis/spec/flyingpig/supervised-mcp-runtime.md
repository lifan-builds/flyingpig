# Supervised MCP Runtime Contract

## 1. Scope / Trigger

Use this contract when changing supervised Chrome DevTools MCP execution, run authorization, completion, duplicate-send prevention, supervisor stop/cancel behavior, helper health, desktop startup, or packaged build identity.

The cross-layer flow is:

```text
McpBrowserExecutor -> AgentBrain -> RunManager -> REST/WebSocket -> dashboard
fresh snapshot -> completion evaluator -> TaskResult -> reconnectable run state
build metadata generator -> helper /health + Electron expected build -> startup UI
```

The helper owns policy and results. The dashboard renders typed state; it does not infer authorization, completion, or browser actions. MCP actions remain allowlisted, all real authentication remains manual, and live customer-service validation remains separately gated.

## 2. Signatures

### Python runtime

```python
class McpBrowserExecutor:
    def __init__(
        self,
        *,
        session_factory=...,
        max_snapshot_chars: int = 12000,
        progress_sink: Callable[[dict], None] | None = None,
        phase_timeouts: dict[str, float] | None = None,
        recent_intent_window: int = 8,
    ) -> None: ...

    def request_stop(self, reason: str | None = None) -> None: ...

    async def run(
        self,
        *,
        task_prompt: str,
        llm,
        page: dict,
        input_handler,
        max_steps: int,
        save_dir,
        authorization: RunAuthorization | None = None,
        fallback_llm=None,
        llm_timeout_seconds: int = 30,
    ) -> TaskResult: ...
```

```python
class AuthorizationTarget(BaseModel):
    key: str
    display: str
    authorized_actions: list[str] = []

class RunAuthorization(BaseModel):
    targets: list[AuthorizationTarget] = []
    target_account: str | None = None
    authorized_actions: list[str] = []
    refund_methods: list[str] = []
    declined_alternatives: list[str] = []
    huca_authorized: bool = False
    user_authorized: bool = False


def authorization_from_payload(payload: dict | None) -> RunAuthorization: ...
```

Both authorization models use `extra="forbid"`.

```python
@dataclass(frozen=True)
class CompletionEvaluation:
    state: Literal["complete", "partial", "incomplete", "unknown"]
    satisfied: bool
    fresh: bool
    items: list[dict]
    unresolved_items: list[str]
    evidence_references: list[dict]
    follow_up_actions: list[dict]


def evaluate_completion(
    workflow_state: ChatWorkflowState,
    authorization: RunAuthorization,
    *,
    fresh: bool,
    snapshot_id: str | None = None,
    accepted_deferred: set[str] | None = None,
) -> CompletionEvaluation: ...
```

Daemon lifecycle endpoints and messages:

- `POST /run/stop` or WebSocket `{"type":"stop"}`: graceful MCP stop and fresh-evidence evaluation.
- `POST /run/cancel` or WebSocket `{"type":"cancel"}`: hard cancellation.
- HUCA/replacement paths use hard cancellation before starting the replacement run.

### Desktop and build APIs

```javascript
compareBuildIdentity(expected, actual)
buildHelperLaunchCommand(options = {})
findAvailablePort({ host = "127.0.0.1", startPort = 8765, maxAttempts = 50 } = {})
waitForHelperReady({ baseUrl, timeoutMs = 30000, intervalMs = 250 } = {})
```

```text
npm run build:metadata
node scripts/generate_build_metadata.mjs
```

`desktop:package`, `desktop:publish`, and `build:helper` run metadata generation first.

## 3. Contracts

### Live progress, timing, and delivery

A phase emits a progress start and terminal event:

```json
{
  "type": "progress",
  "phase": "planner_call",
  "state": "starting | complete | timeout | failed",
  "step": 1,
  "message": "fixed safe copy",
  "timestamp": "UTC ISO-8601",
  "error_category": "optional safe category"
}
```

Timing spans use:

```json
{
  "type": "timing_span",
  "name": "planner_call",
  "label": "fixed safe label",
  "duration_ms": 12.3,
  "status": "ok | timeout | failed",
  "timestamp": "UTC ISO-8601",
  "metadata": {"step": 1},
  "error_category": "optional safe category"
}
```

Stable phases and default bounds are:

| Phase | Timeout seconds |
|---|---:|
| `process_session_setup` | 15 |
| `page_selection` | 60 |
| `tool_discovery` | 30 |
| `first_snapshot` | 60 |
| `planner_call` | 180, or `max(llm_timeout_seconds * 2 + 5, 10)` for the active call |
| `browser_action` | 95 |
| `snapshot_refresh` | 60 |
| `completion_evaluation` | 5 |

Safe error categories are `timeout`, `cancelled`, `mcp_unavailable`, `invalid_output`, `process_unavailable`, and `operation_failed`.

`McpBrowserExecutor` appends a copy to its own log and immediately publishes another copy through `progress_sink`. `AgentBrain` owns the shared append-only stream. `RunManager` owns one locked cursor per run, polls in source order, advances only after state application/broadcast, and performs a final drain before `result_ready`. Final drain and polling may race, so cursor idempotency—not event deduplication by content—prevents duplicate delivery.

Progress and timing must never contain prompts, model output, snapshots, tool arguments/results, chat text, authorization target values, private URLs, credentials, environment values, command lines, or user paths.

### Target-scoped authorization

Normalize strings by trimming them; discard empty list entries and preserve first-seen order while deduplicating.

- Non-empty structured `targets` take precedence and clear legacy `target_account` plus global `authorized_actions`.
- With no structured targets, legacy `target_account` plus global actions becomes exactly one target with key `legacy-target`.
- `user_authorized=true` with no concrete target/action grants no consequential permission.
- `permits(action)` without a target succeeds only when exactly one authorized target permits it.
- Multi-target visible-text resolution succeeds only when exactly one permitted target display matches; otherwise checkpoint instead of guessing.
- Dashboard payloads assign permissions per target row; never derive every target's actions from aggregate checkboxes.

### Fresh completion and deferred work

- `fresh=false` always yields `unknown`, unsatisfied.
- A fresh snapshot with no authorized checklist yields `unknown`, unsatisfied.
- Multi-target evidence must identify the concrete target; one target's evidence cannot complete another.
- Confirmed refund methods are intersected with `authorization.refund_methods`; visible text cannot broaden allowed methods.
- Unresolved items yield `incomplete`.
- Accepted deferred keys use `<target_key>:<action>`; refund follow-up uses `credit_refund_disposition`.
- Deferred work resolves loop termination only after visible acceptance. It yields `partial`, `satisfied=true`, and a pending follow-up action—not success.
- With all items complete and no deferred work, return `complete` and success.
- `report_outcome` is optional planner summary input; deterministic evaluation of the latest fresh snapshot remains authoritative.

Serialized result details include `completion_evaluation`, `completion_checklist`, `unresolved_items`, `evidence_references`, and `follow_up_actions`. Evidence references include `snapshot_id` when available.

### Recent-intent duplicate guard

Apply layers in this order:

1. Normalize whitespace and reject empty outbound text.
2. Check target-scoped exact SHA-256 digest and parsed transcript exact text.
3. Derive a deterministic semantic key from target plus intent class.
4. Suppress the same key only inside the 90-second window and count-bounded deque (default 8, effective minimum 1).
5. Record the exact digest and intent key only after composer replacement, exact-value verification, Send click, and post-send transcript verification.

Known intent classes include consent, close request, refund request, and status check. Close/refund keys include operative modifiers such as amount, confirmation, email, fee, method, reason, and timing. Corrections and unknown/materially different intents fail open. The same intent for a different target remains sendable. Suppression occurs before composer interaction and never clicks Send.

### Graceful stop and hard cancellation

Graceful MCP stop sets a stop event checked after completion evaluation, before browser actions, after actions, before composer fill, and after exact composer verification immediately before Send. After a settled action, refresh and re-evaluate the latest snapshot.

A graceful result includes:

```json
{
  "termination_reason": "supervisor_stop",
  "supervisor_stop_reason": "bounded to 160 characters",
  "stop_evaluation": "success | partial | stopped_with_no_result | failed_to_evaluate",
  "supervisor_stopped": true
}
```

Fresh complete evidence maps to success. Grounded partial/incomplete evidence maps to partial. No grounded item maps to `stopped_with_no_result`. Evaluation failure or the daemon's 120-second graceful-stop timeout maps to `failed_to_evaluate`; it must retain the supervisor-stop marker.

Hard cancellation cancels observers and the agent, waits at most 15 seconds, and stores `cancelled`. Use hard cancel for `/run/cancel`, shutdown/teardown, HUCA, and replacement runs. A non-MCP `stop()` falls back to hard cancellation.

### Planner envelope normalization

Accepted shapes are a flat action or one allowlisted wrapper:

```json
{"action": "click", "uid": "synthetic-id"}
{"action": {"action": "report_outcome", "outcome": "done"}}
{"result": {"action": "report_outcome", "outcome": "done"}}
```

Exactly one wrapper key (`action` or `result`) is allowed, with no sibling fields and no recursive executable object. The inner action must be a string. After unwrapping, strict `McpAgentAction(extra="forbid")` validation and `ALLOWED_ACTIONS` checks run. Reject lists, multiple candidates, sibling conflicts, recursive wrappers, unknown fields/actions, and textual completions containing a second decodable JSON object or list before any browser tool call.

### Build identity and startup diagnostics

Metadata generator inputs:

- Revision: valid `FLYINGPIG_BUILD_REVISION`, else short Git revision, else `null`.
- Timestamp: positive numeric `SOURCE_DATE_EPOCH`, else commit epoch, else `null`.
- Channel: valid `FLYINGPIG_BUILD_CHANNEL`, else `packaged`.
- Revision must match `^[a-f0-9]{7,40}$` (case-insensitive); channel must match `^[A-Za-z0-9._+-]{1,40}$`.

Generated Python uses `revision`, `built_at`, `channel`; generated JavaScript uses `revision`, `builtAt`, `channel`. Development defaults are null revision/time and channel `development`.

Helper `/health.build` contains `version`, `revision`, `built_at`, `channel`, and display-only `identity`. Desktop comparison uses version, revision, timestamp, and channel fields—not the formatted identity string. Missing version is `unknown`; any available version/revision/timestamp mismatch is `mismatch`; channel mismatches only when both channels are present.

Startup phases are `port_selection -> spawn -> health_wait -> ready`. Failure phases/categories are `port_selection`, `spawn`, `early_exit`, and `health_wait`. The supervisor checks at most 50 consecutive ports and reports whether the preferred port was occupied.

Safe desktop diagnostics may contain `baseUrl`, selected/preferred local port, fallback flag, phase, running state, scrubbed `lastError`, expected/actual build, `buildMatch`, and `logsAvailable`. They must omit command, arguments, cwd, environment values, log path, port-owner details, and unrelated process data.

## 4. Validation & Error Matrix

| Condition | Required result |
|---|---|
| Blocking MCP phase exceeds bound | Terminal `timeout` progress/timing event; typed safe phase error |
| Final progress arrives while polling ends | Final drain broadcasts once before `result_ready` |
| Empty target key/display or duplicate key | Authorization validation error |
| Structured targets plus legacy actions | Structured targets win; legacy target/actions are cleared |
| Generic authorization without target/action | Deny consequential action |
| Multiple targets match or none match | Checkpoint/ambiguity result; never guess |
| Stale completion evidence | `unknown`, unsatisfied |
| Offered deferred work not visibly accepted | `incomplete` |
| Accepted deferred work | `partial`, pending follow-up, never success |
| Visible refund method not authorized | Remains unresolved |
| Same target/intention inside 90 seconds | Suppress before fill/click |
| Correction, material modifier, or different target | Allow normal verified-send path |
| Stop before fill or immediately before Send | No Send click; evaluate fresh state |
| Stop evaluation fails/times out | Preserve `supervisor_stop`; `failed_to_evaluate` |
| HUCA/replacement | Hard cancel abandoned run; do not preserve success |
| Ambiguous/multiple/recursive planner payload | Reject before tool execution |
| Invalid build env override | Ignore invalid value and use safe fallback/null |
| Missing build version | `buildMatch="unknown"` |
| Available identity field mismatch | `buildMatch="mismatch"` |
| Preferred port occupied | Select next bounded port and expose fallback flag only |
| Spawn/health failure | Safe phase/category; no command/env/path leakage |

## 5. Good / Base / Bad Cases

**Good**

- Two targets have different action sets; consent names and authorizes exactly one.
- Fresh evidence resolves all authorized items before another planner call.
- A polite same-target consent rewrite is suppressed, while a new email-confirmation question sends.
- Supervisor stop after verified completion returns success with `termination_reason="supervisor_stop"`.
- Reproducible metadata uses `SOURCE_DATE_EPOCH`, and desktop/helper fields compare as `match`.

**Base / neutral**

- `RunAuthorization(user_authorized=True)` grants no consequential action.
- Fresh state with no authorized checklist remains `unknown`.
- Unknown message intent gets no semantic key and uses exact/transcript checks only.
- A development build reports a development/unknown identity rather than inventing a revision.

**Bad**

- Applying aggregate actions to every structured target.
- Completing target B from evidence that only names target A.
- Treating accepted deferred work as full success.
- Suppressing corrections or materially new questions.
- Storing graceful stop as bare `cancelled`, or preserving an abandoned HUCA run as success.
- Accepting recursive/multiple planner actions.
- Comparing only formatted identity strings.
- Displaying executable paths, environment values, command lines, or raw startup errors.

## 6. Tests Required

At minimum, maintain these assertion groups:

- `tests/unit/test_mcp_executor.py`
  - progress is visible while planner remains blocked and contains no prompt/snapshot sentinel;
  - all eight phases emit bounded timeout progress/timing;
  - multi-target consent is target-bound or checkpointed;
  - stop before Send produces no click and stop evaluation preserves success/partial/failure markers;
  - recent-intent variants suppress only for the same target and window, while corrections/material changes send;
  - flat and one-level `action`/`result` envelopes pass, while recursive/ambiguous/multiple JSON fails before tool execution.
- `tests/unit/test_run_authorization.py`
  - structured targets clear legacy global scope;
  - legacy scope creates exactly one `legacy-target`;
  - generic authorization grants nothing;
  - empty/duplicate/extra target data fails and nested authorization precedence is stable.
- `tests/unit/test_chat_workflow.py`
  - stale, target-mismatched, complete, incomplete, deferred-unaccepted, deferred-accepted, and unauthorized-refund-method cases;
  - accepted deferred output remains partial and carries pending follow-up plus snapshot reference.
- `tests/unit/test_daemon_server.py`
  - live state/WebSocket progress, locked cursor final drain exactly once before result, graceful stop preservation, hard cancel/HUCA separation, and safe `/health.build`.
- `desktop/helper_supervisor.test.mjs` and `desktop/build_metadata.test.mjs`
  - identity match/mismatch/unknown, reproducible inputs, invalid override fallback, port fallback/exhaustion, ordered startup phases, early exit, spawn failure, health timeout, and diagnostic field omission.
- Dashboard protocol/smoke tests
  - target rows serialize separate permissions; progress/startup/build mismatch and completion/follow-up states render without frontend policy inference.

Run the full safe gate in [Verification](verification.md). Real Chrome, authenticated customer-service, package publishing, signing, notarization, and release replacement remain separately gated and are not routine acceptance tests.

## 7. Wrong vs Correct

| Wrong | Correct |
|---|---|
| Copy executor logs only after `run()` returns | Publish through `progress_sink` during execution; daemon owns one locked cursor and final drain |
| Put snapshot/prompt text in progress | Emit fixed phase/state/message, step, time, duration, and safe category only |
| Apply global actions to all targets | Structured targets own per-target actions; legacy scope normalizes to one target only |
| Guess a target from task prose | Resolve exactly one authorized target or checkpoint |
| Trust planner `report_outcome` | Evaluate the latest fresh snapshot deterministically |
| Treat accepted deferred work as success | Return satisfied partial with pending follow-up |
| Use unbounded semantic similarity | Use deterministic target-scoped keys with bounded count/time windows |
| Record duplicate state before verification | Record only after verified send; suppress before composer interaction |
| Implement stop by cancelling and erasing result | Block future sends and evaluate fresh evidence; keep hard cancel separate |
| Use graceful stop for HUCA | Hard-cancel abandoned run before replacement |
| Execute arbitrary nested planner output | Unwrap one allowlisted envelope, then strict schema and allowlist |
| Compare only a display identity string | Compare version, revision, timestamp, and channel fields |
| Expose launch internals for diagnosis | Expose safe phase, port fallback, build match, scrubbed error, and logs availability |
