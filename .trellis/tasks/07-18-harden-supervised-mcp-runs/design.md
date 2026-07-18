# Technical design: supervised MCP safety and observability

## Design principles

1. Fresh visible evidence owns completion; neither planner prose nor supervisor belief can manufacture success.
2. Authorization is explicit, structured, and target-scoped before any consequential message is composed.
3. The supervisor can halt future actions without erasing already-grounded work.
4. Observability reports phases, durations, counts, and safe categories—not page content or customer data.
5. Recovery is bounded: normalize known envelopes and message intents without widening executable behavior.

## Architecture and boundaries

### Shared live progress sink

Give `McpBrowserExecutor` an injected append-only progress sink or callback owned by `AgentBrain`. `_record_step` and a new phase/timing helper publish directly into that sink while the run is active. `RunManager._poll_progress()` remains the sole websocket/state broadcaster and advances by cursor so event delivery stays ordered and idempotent.

Progress events should use a small schema such as:

- `type`: `progress` or `timing_span`
- `phase`: stable enum-like name
- `state`: `starting`, `complete`, `timeout`, or `failed`
- `step`: optional action-loop step
- `duration_ms`: only when known
- `error_category`: optional safe category
- `message`: fixed user-facing text

Never include snapshot text, model prompts/completions, tool arguments/results, chat text, account targets, or URLs.

### Phase timeouts

Wrap blocking calls with a reusable async phase runner that:

- publishes start and finish/failure events;
- measures elapsed time;
- applies an explicit timeout;
- maps exceptions to bounded safe categories;
- re-raises the original typed failure for existing result handling.

Keep planner primary/fallback behavior intact. MCP process launch/session setup may require instrumentation in `src/agent/chrome_devtools_mcp.py`; action-loop instrumentation belongs in `src/agent/mcp_executor.py`.

### Structured authorization targets

Introduce a target model containing a stable opaque target key or display suffix, plus the exact permitted actions for that target. The run authorization owns an ordered list of targets. A compatibility validator converts legacy `target_account` plus global `authorized_actions` into one target, without inferring missing values.

Consequential workflow actions receive a concrete target context. If multiple pending targets are possible and the transcript cannot safely identify one, return a decision checkpoint or structured ambiguity result. Consent rendering accepts one target object, never a joined string.

Do not persist real target values in test fixtures or diagnostic events; use synthetic placeholders.

### Completion evaluator

Extract completion evaluation from planner-only `report_outcome` handling into a deterministic function over:

- the latest parsed workflow state;
- structured authorization targets/actions;
- accepted deferred dispositions;
- snapshot freshness metadata.

Return a structured evaluation with overall state (`complete`, `partial`, `incomplete`, `unknown`), per-target items, unresolved items, safe evidence references, and follow-up actions. Run it after the initial snapshot and every refreshed snapshot, before planning another outbound action. If complete, finalize immediately. `report_outcome` becomes an optional summary input validated against the same evaluator.

### Recent-intent duplicate guard

Use deterministic canonicalization rather than an external model or similarity service. Derive a small intent key from:

- consequential action class (for example consent, close request, fee-refund request, status check);
- concrete target key;
- normalized operative terms;
- a bounded recent-message/action window.

Retain exact hash checks as the first layer. The semantic layer may normalize casing, punctuation, polite fillers, equivalent consent phrases, and target ordering. It must fail open for unknown or materially different intents, while known consequential repeated intents fail closed. Record the intent category, not message text, in progress/action diagnostics.

### Supervisor stop protocol

Add a graceful supervisor-stop path distinct from hard cancellation:

1. Set an atomic/async stop-request flag that prevents the next outbound action.
2. Allow the current bounded browser call to settle or cancel it at a safe boundary.
3. Obtain/reuse the latest fresh snapshot.
4. Run the completion evaluator.
5. Persist a result with `termination_reason=supervisor_stop` and evaluation status.
6. Tear down observers and the agent task.

Keep hard cancellation for app shutdown, failed startup, and HUCA/replacement flows. If snapshot evaluation fails, preserve a stopped-with-no-result or prior structured partial result; never overwrite it with bare `cancelled` unless hard cancel was requested.

### Planner envelope normalization

Before `McpAgentAction` validation, unwrap only a whitelist of one-level containers such as `{"action": { ...action fields... }}` or another confirmed CLIProxy key. Require exactly one candidate mapping. Reject lists, multiple candidates, recursive wrappers, conflicting outer/inner action fields, and unknown executable shapes. Then run normal Pydantic validation and the existing allowlist check.

Normalization failures produce a safe category and may trigger one existing fallback/retry. They must never reach `session.call_tool`.

### Build and startup diagnostics

Generate build metadata during helper/desktop packaging and expose it through helper health plus desktop status. Suggested fields:

- application version;
- short source revision when available;
- build timestamp;
- build channel or `development` marker;
- helper identity for mismatch detection.

The desktop supervisor should record startup phases (`port_selection`, `spawn`, `health_wait`, `ready`) and whether it fell back from the preferred port. The UI should show safe actionable summaries and the logs location. Port-owner process inspection, if implemented, must be local-only, bounded, and scrubbed; the normal UI only needs to say the preferred port was occupied and which port was selected.

## Data-flow changes

```text
RunManager
  -> AgentBrain owns live progress sink and stop signal
    -> McpBrowserExecutor publishes safe phase events
      -> snapshot -> workflow parse -> completion evaluation
        -> complete: structured result, no more outbound action
        -> incomplete: target-scoped action planning/execution
          -> exact + intent duplicate guard
          -> verified composer send

Supervisor stop
  -> stop signal -> safe action boundary -> latest snapshot
  -> same completion evaluator -> preserved structured result
```

## Compatibility and migration

- Accept legacy single-target authorization payloads and normalize them in one place.
- Version structured result additions additively; existing dashboard fields remain populated.
- Keep hard-cancel API semantics for current internal replacement flows. Add an explicit graceful stop mode rather than silently changing every cancellation caller.
- Non-MCP browser execution continues to use its current progress and outcome paths unless shared schema adapters are needed.

## Operational and rollback considerations

- Land changes in separable phases so live progress can ship independently of authorization/result schema changes.
- Guard new graceful-stop and semantic-intent behavior with focused unit tests before desktop wiring.
- If a new completion evaluator proves too aggressive, disable proactive completion while retaining the evaluator for supervisor-stop result preservation; do not remove authorization or verified-send checks.
- If build metadata is absent, render `unknown/development` explicitly instead of guessing freshness.
