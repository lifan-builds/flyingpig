# Implementation plan: supervised MCP safety and observability

## Handoff context

- Parent task: `07-12-prepare-next-supervised-beta-run`.
- The external supervised smoke achieved its authorized goal, but Flying Pig required a supervisor stop after it continued sending repetitive messages.
- The authenticated chat was left open for user review; implementation must not depend on or capture that private browser state.
- Current source was rebuilt before the smoke, and Chrome DevTools MCP already launches with `@latest`. The missing freshness signal is Flying Pig's packaged build identity.
- No product-code fixes were made during the live run. Preserve the pre-existing `.codex/config.toml` user change.
- This task is planning-only until separate implementation approval.

## Ordered implementation checklist

### Phase 1: Live progress and diagnostics

- [x] Read the applicable `.trellis/spec/` guidance with `trellis-before-dev` before editing.
- [x] Add a shared live progress sink/callback between `AgentBrain` and `McpBrowserExecutor`.
- [x] Add safe MCP setup/planner/action/snapshot/completion phase events and timing spans.
- [x] Add bounded timeouts and safe error categories for blocking phases.
- [x] Add tests proving progress is visible before executor completion and contains no prompt/snapshot data.

### Phase 2: Authorization and deterministic completion

- [x] Introduce structured per-target authorization with legacy single-target normalization.
- [x] Refactor consent/action generation to require one concrete target.
- [x] Extract a deterministic fresh-snapshot completion evaluator with per-target checklist results.
- [x] Invoke completion evaluation before planning another outbound action.
- [x] Add multi-target, ambiguous-target, stale-evidence, complete, partial, and deferred tests.

### Phase 3: Duplicate and planner-output guards

- [x] Retain exact duplicate hashes and add a bounded deterministic recent-intent key/window.
- [x] Ensure different targets and materially different questions remain sendable.
- [x] Add a one-level allowlisted planner-envelope normalizer before strict schema validation.
- [x] Add tests for supported nested CLIProxy output and rejection of ambiguous/multiple/over-nested actions.

### Phase 4: Graceful supervisor stop

- [x] Add an explicit graceful stop request separate from hard cancellation.
- [x] Prevent new outbound actions after the stop request reaches a safe boundary.
- [x] Reuse the completion evaluator on the latest fresh snapshot and persist structured success/partial/no-result semantics.
- [x] Preserve timing spans, safe evidence, and a supervisor-stop termination marker.
- [x] Keep HUCA/replacement and teardown paths on hard cancellation; add regression tests.

### Phase 5: Desktop startup and build identity

- [x] Define generated build metadata for helper and Electron packaging.
- [x] Expose safe build identity through helper health/diagnostics and the desktop status/dashboard.
- [x] Add startup phase and preferred-port fallback diagnostics.
- [x] Add desktop/helper-supervisor tests for build mismatch, occupied preferred port, early exit, and readiness timeout.

### Phase 6: Integration verification

- [x] Run focused unit tests after each phase.
- [x] Run the Trellis quality gate and relevant dashboard/desktop smoke scripts.
- [x] Inspect tracked changes and generated test artifacts for PII/private browser data.
- [x] Perform only synthetic/local browser validation unless the user separately authorizes another supervised authenticated smoke.
- [x] Update `.trellis/spec/` with durable contracts discovered during implementation, especially progress-event privacy, target-scoped authorization, completion freshness, and stop semantics.

## Likely files

- `src/agent/brain.py`
- `src/agent/mcp_executor.py`
- `src/agent/chat_workflow.py`
- `src/agent/run_authorization.py`
- `src/agent/chrome_devtools_mcp.py`
- `src/agent/result.py`
- `src/daemon/server.py`
- `src/daemon/run_session.py`
- `desktop/helper_supervisor.js`
- `desktop/main.js`
- `desktop/status.js`
- `dashboard/dashboard.js`
- `tests/unit/test_mcp_executor.py`
- `tests/unit/test_chat_workflow.py`
- `tests/unit/test_run_authorization.py`
- `tests/unit/test_daemon_server.py`
- `desktop/helper_supervisor.test.mjs`
- relevant dashboard/desktop smoke scripts

## Validation commands

Run the repository-supported equivalents if project tooling changes:

```bash
pytest -q tests/unit/test_mcp_executor.py tests/unit/test_chat_workflow.py tests/unit/test_run_authorization.py tests/unit/test_daemon_server.py
npm test -- --runInBand
node scripts/test_dashboard_protocol.mjs
node scripts/test_desktop_shell.mjs
python3 ./.trellis/scripts/task.py validate 07-18-harden-supervised-mcp-runs
```

Before completion, use `trellis-check` for the full project quality gate rather than assuming the focused commands are sufficient.

## Risky changes and rollback points

- Authorization schema migration can silently broaden or narrow consequential scope. Centralize legacy conversion and test deny-by-default behavior.
- Proactive completion can stop too early if transcript parsing is over-broad. Require fresh evidence and per-target checklist coverage; keep a feature-level rollback path.
- Semantic duplicate suppression can hide legitimate follow-ups. Keep the window bounded and deterministic, with explicit different-target and correction cases.
- Graceful stop races with active sends. Check the stop signal immediately before composer fill and immediately before Send; preserve verified-send accounting if a click already occurred.
- Progress callbacks cross async/thread boundaries. Keep publication append-only and avoid exposing mutable executor internals.
- Build metadata generation must be reproducible and must not fail development launches when Git metadata is unavailable.

## Pre-start gate

- [x] User explicitly approved implementation on 2026-07-18 by instructing the agent to continue until all remaining tasks are complete.
- [x] Task remains the intended follow-up child of the archived supervised-beta parent.
- [x] Applicable Trellis specs are curated in the sub-agent manifests; no conflicting product decision was found.
- [x] No authenticated smoke or external account action is included in the implementation plan without separate approval.
- [x] `implement.jsonl` and `check.jsonl` contain real curated spec entries for sub-agent dispatch.
