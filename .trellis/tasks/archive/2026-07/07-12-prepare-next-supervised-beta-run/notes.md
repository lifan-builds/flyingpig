# Supervised beta run notes

## PII-free outcome

- A supervised smoke on a supported customer-service surface reached a human representative and achieved the authorized closure/refund goal.
- Fresh visible evidence indicated the authorized outcome and expected follow-up before the supervisor stopped further agent actions.
- Private browser state remains local. No account identifiers, amounts, transcript text, authentication data, private URLs, confirmation values, or browser-session details are recorded here.

## Acceptance evidence and blockers

1. **Current packaged build and dashboard readiness: verified for next-run preparation.** Helper and Electron package version 1.0.2 were rebuilt on 2026-07-18, the packaged Electron app was relaunched, and its packaged helper returned healthy. A window-level visual check confirmed that the packaged shell loaded the configured-user dashboard at sequential first-run Step 2 without opening the work window. The same packaged dashboard source was then exercised with the repository's local mock helper in a fresh temporary browser profile; visual checks covered Steps 1–3 and the request, preparation, running, decision, and result surfaces. The temporary profile and mock helper were removed/stopped after inspection. No authenticated browser or external customer-service surface was opened. This evidence prepares the next run and does not retroactively establish build ordering for the earlier smoke.
2. **Preferred and fallback model readiness: verified for next-run preparation.** Before any customer-service attachment, the configured CLIProxy preferred model (`gpt-5.6-luna`) passed a generic readiness probe in under one second, and its bounded fallback (`gpt-5.4-mini`) passed separately in under two seconds. No page, customer, credential, endpoint, prompt, or response data is recorded.
3. **Supervised boundary compliance: not verified as a clean completion.** The authorized goal was visibly achieved, but the parent-task evidence does not establish that every explicit send, checkpoint, irreversible action, and recovery boundary was observed. Repetitive post-success sends required a supervisor stop, so this run is recorded as a blocker rather than claimed as a fully compliant smoke.
4. **Fresh evidence and result distinction: partially verified.** Fresh visible evidence supported the external outcome, while the application retained only a cancelled run state after the supervisor stop. The external outcome and the software-result defect are intentionally reported separately.
5. **Privacy review: verified for this artifact.** Only coarse status, goal class, and technical blockers are recorded; private run content and local state are excluded.
6. **Follow-on scope: deferred.** Safety/observability hardening is planned separately in `07-18-harden-supervised-mcp-runs`. Metrics measurement, adapter expansion, publishing, signing, notarization, and release replacement remain deferred and require their own reviewed tasks if pursued.

## Gaps observed

1. **Packaged build freshness is not visible.** The initially running desktop package predated later source/dashboard changes, but the UI gave no build commit or timestamp. A supervised run can unknowingly exercise stale code.
2. **Helper port conflicts stall startup without actionable UI.** An unrelated process on the default helper port left the app at `Starting local helper` until the port owner was diagnosed externally.
3. **MCP progress is not live.** `AgentBrain` copies `McpBrowserExecutor.step_log` only after `executor.run()` returns, so the dashboard and `/run/state` remain at `Starting agent` while the agent is actively working.
4. **Helper logs lack safe MCP phase diagnostics.** The log showed HTTP access but not bounded, PII-free stages such as page selection, tool discovery, first snapshot, planner call, or action execution. This made a healthy active run look wedged.
5. **Structured action recovery is too narrow.** One configured CLIProxy planner returned a nested action object instead of the required flat `action` field, causing immediate validation failure rather than a bounded normalization/retry.
6. **Completion detection failed after success.** After fresh visible evidence indicated the authorized outcome, the agent continued sending repeated consent and confirmation requests instead of reporting completion.
7. **Aggregate authorization targets can produce malformed consent text.** A multi-account target description was inserted into a singular `card ending in ...` consent template. Consent messages must bind to one concrete target at a time.
8. **Duplicate suppression is exact-text only.** Semantically equivalent consent/request messages with small wording differences bypassed hash-based suppression and were sent repeatedly.
9. **Supervisor cancellation discards the successful result.** Stopping a misbehaving agent after fresh visible success leaves run state as `cancelled` with no structured partial/supervisor-confirmed outcome.

## Suggested follow-up scope

- Stream the executor step log live and add safe timing spans/timeouts around MCP setup and planner phases.
- Normalize or retry common structured-action envelope variants without widening the action allowlist.
- Make authorization and consent target-aware for multi-account tasks.
- Add semantic/recent-intent duplicate protection and a completion guard based on fresh transcript evidence.
- Let a supervisor stop further actions while preserving a structured success/partial result grounded in the latest snapshot.
- Surface packaged build identity and port-conflict diagnostics in the desktop startup UI.
