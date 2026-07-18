# Harden supervised MCP run safety and observability

## Goal

Make supervised Chrome MCP runs observable, bounded, and safely stoppable while preserving Flying Pig's autonomous execution model, explicit authorization boundaries, verified sends, and evidence-grounded completion.

## Background

A supervised authenticated customer-service beta run completed its authorized external goal, but the supervisor had to stop the agent after fresh visible success because the agent continued sending semantically repetitive messages. During the same run, the dashboard showed little useful progress, structured planner output failed on a common envelope variant, multi-target consent wording was malformed, and cancellation erased the successful outcome.

The evidence for this task is intentionally PII-free. Do not add account identifiers, amounts, transcript text, private URLs, authentication data, screenshots, recordings, cookies, or browser-session state to tracked artifacts, fixtures, logs, or test output.

## Confirmed Technical Facts

- MCP progress is copied from the executor only after `executor.run()` returns, so active events are invisible through the brain and daemon polling path (`src/agent/brain.py:214`, `src/agent/brain.py:231`, `src/daemon/server.py:461`).
- MCP setup performs page selection, tool discovery, and the first snapshot before the first recorded step; those phases have no bounded, PII-safe diagnostics (`src/agent/mcp_executor.py:107`, `src/agent/mcp_executor.py:127`).
- Planner output coercion accepts only a flat action object and does not normalize a bounded nested action envelope (`src/agent/mcp_executor.py:612`).
- Completion relies on a transcript-derived checklist and a planner-issued `report_outcome`; the executor has no proactive completion guard after a fresh snapshot satisfies all authorized items (`src/agent/mcp_executor.py:319`, `src/agent/chat_workflow.py:44`).
- Duplicate suppression hashes exact normalized text only, allowing semantically equivalent recent messages to be sent (`src/agent/mcp_executor.py:390`).
- Authorization currently models one free-form `target_account`, while automated consent inserts it into a singular sentence (`src/agent/run_authorization.py:8`, `src/agent/mcp_executor.py:432`).
- Run cancellation always writes `cancelled` and does not preserve a fresh successful or partial result (`src/daemon/server.py:531`, `src/daemon/server.py:551`).
- The desktop helper supervisor can choose an available port and waits up to 30 seconds for health, but its visible diagnostics omit build identity and port-selection/owner detail (`desktop/helper_supervisor.js:87`, `desktop/helper_supervisor.js:99`, `desktop/helper_supervisor.js:177`, `desktop/status.js:3`).
- The default Chrome DevTools MCP launch command already resolves `chrome-devtools-mcp@latest`; build freshness of Flying Pig itself is still not visible (`src/agent/chrome_devtools_mcp.py:24`).

## Requirements

### R1. Live MCP progress and safe diagnostics

- Expose executor progress to `AgentBrain.step_log` while `McpBrowserExecutor.run()` is active, without polling private snapshots or copying transcript content into progress events.
- Emit bounded phase events and timing spans for MCP process/session setup, page selection, tool discovery, first snapshot, planner call, browser action, snapshot refresh, and completion evaluation.
- Give each blocking phase an explicit timeout or reuse a documented bounded timeout. Failures must identify the phase and safe error category without including page text, planner prompts, tool payloads, or credentials.
- Preserve event ordering and avoid duplicate delivery when the daemon polls the shared progress stream.

### R2. Target-scoped authorization for multi-target work

- Replace ambiguous aggregate target text with a structured collection of concrete authorization targets and permitted actions per target.
- Bind every automatically generated consequential message to exactly one authorized target at a time.
- Preserve compatibility for existing single-target payloads through a narrow migration path; do not infer targets or permissions from the natural-language task.
- Reject or checkpoint when a consequential action cannot be mapped unambiguously to one structured target.

### R3. Evidence-grounded completion guard

- After each fresh snapshot, evaluate whether every authorized goal item is complete, deferred with an accepted disposition, or still unresolved.
- When all authorized items are satisfied by fresh visible evidence, stop further outbound actions and produce a structured result even if the planner fails to call `report_outcome`.
- Do not report success from stale state, the task prompt, prior snapshots, or supervisor assertion alone. Preserve evidence references in the existing safe structured result shape.
- Keep partial and follow-up dispositions distinct from full success.

### R4. Semantic recent-intent duplicate suppression

- Continue exact-text and transcript duplicate checks, then add a deterministic, bounded recent-intent guard for outbound chat messages.
- Treat small wording, punctuation, politeness, and target-order variations as duplicates when they express the same recent consequential intent for the same target.
- Do not suppress a materially new question, a requested correction, a status response after a defined wait window, or the same action for a different target.
- A suppressed message must be recorded as a safe action result and must not click Send.

### R5. Supervisor stop that preserves outcome

- Separate "stop further actions" from "discard run result."
- On supervisor stop, capture or reuse the latest fresh snapshot, run the same completion evaluation, and persist one of: success, partial, stopped-with-no-result, or failed-to-evaluate.
- Record that the supervisor stopped execution and why, while retaining timing spans and any already-grounded outcome. Do not convert an unverified supervisor belief into success.
- Keep the existing hard-cancel behavior available for teardown and replacement-run flows such as HUCA.

### R6. Bounded structured-action normalization

- Normalize only explicitly supported planner envelopes, including a single nested action object from CLIProxy-style structured output.
- Apply the existing `McpAgentAction` schema and action allowlist after unwrapping; never execute arbitrary nested tool calls or unknown fields as actions.
- Reject ambiguous envelopes, multiple candidate actions, excessive nesting, or schema conflicts with a safe diagnostic and at most one bounded retry/fallback.

### R7. Startup and build identity diagnostics

- Surface a Flying Pig build identifier in the packaged desktop status/dashboard and helper health diagnostics. Prefer version plus commit/build timestamp when available and a clear development-build marker otherwise.
- Report helper startup phases, selected port, whether the preferred port was occupied, and actionable timeout/early-exit diagnostics.
- Do not expose full process command lines, environment variables, user paths, or unrelated port-owner details in normal UI. More detailed local diagnostics may remain in the logs folder if scrubbed of secrets.
- Distinguish a stale/mismatched helper build from a healthy current package when both identities are available.

### R8. Safety and compatibility invariants

- Preserve the narrow MCP action allowlist, exact composer replacement, pre-send verification, post-send transcript verification, explicit authorization, decision checkpoints, and existing browser attachment boundaries.
- Keep logs, progress events, tests, and Trellis artifacts PII-free.
- Preserve current non-MCP behavior unless a shared contract must change; add compatibility tests when shared result or authorization schemas change.

## Acceptance Criteria

- [ ] During a deliberately delayed MCP run, `/run/state` and websocket progress advance through safe setup/planner/action phases before the executor finishes; no event contains snapshot or prompt text. (R1)
- [ ] Each MCP setup/planner/action phase has a bounded timeout and a unit test for success plus at least one timeout/failure path. (R1)
- [ ] A two-target authorization fixture generates separate target-bound consent/actions and never renders aggregate text in a singular template. (R2)
- [ ] Legacy single-target authorization remains accepted and is normalized without broadening permissions. (R2)
- [ ] A fresh transcript fixture satisfying all authorized checklist items causes automatic completion before any subsequent outbound message. (R3)
- [ ] Incomplete, stale, and deferred fixtures produce the correct unresolved/partial state rather than false success. (R3)
- [ ] Semantically equivalent recent consent/request variants for the same target result in one verified send; materially distinct messages and different targets are not suppressed. (R4)
- [ ] Supervisor stop after fresh visible completion preserves a structured successful result with a supervisor-stop marker; stop before completion preserves partial/no-result semantics. (R5)
- [ ] HUCA/replacement cancellation remains a hard cancellation and does not accidentally preserve the abandoned run as success. (R5)
- [ ] A supported single nested CLIProxy action envelope is normalized and validated; ambiguous, multi-action, over-nested, or unsupported envelopes fail without executing a browser action. (R6)
- [ ] The desktop startup/status surface shows build identity, selected helper port, and actionable startup failure phases without exposing secret environment or private browser data. (R7)
- [ ] Existing verified-send, authorization, checkpoint, MCP allowlist, daemon lifecycle, desktop supervisor, and non-MCP regression tests pass. (R8)
- [ ] New fixtures and tracked diagnostics contain no real customer identifiers, amounts, transcript excerpts, URLs, credentials, or session state. (R8)

## Out of Scope

- Re-running an authenticated customer-service task as part of implementation.
- Broadening the MCP browser action allowlist or enabling arbitrary JavaScript execution.
- Replacing Chrome DevTools MCP, the planner provider, or the Electron shell.
- General-purpose semantic similarity services, vector databases, transcript retention, or remote telemetry.
- Publishing, signing, notarizing, or replacing release artifacts.
- Measuring public-beta success-rate targets or expanding site-adapter coverage.

## Implementation Approval

On 2026-07-18, the user explicitly instructed the agent to continue working until all remaining tasks are complete, approving implementation of this child task. Authenticated customer-service smoke, publishing, signing, notarization, and other gated external operations remain out of scope without separate explicit approval.
