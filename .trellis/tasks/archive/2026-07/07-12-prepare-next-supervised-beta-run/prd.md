# Prepare next supervised beta run

## Goal

Prepare and execute the next supervised public-beta validation without storing private account, chat, authentication, or browser-session details in Trellis artifacts.

## Requirements

- Rebuild and relaunch the desktop app/helper before visual validation so the running package includes the current dashboard and browser flows.
- Visually confirm the configured-user dashboard in the packaged Electron shell, including the sequential first-run path and state-driven request/preparation/running/decision/result surfaces.
- Configure and harmlessly probe a preferred fallback model/provider before attaching to an authenticated customer-service surface; do not put provider credentials or probe payloads in the task.
- Run any real customer-service beta smoke only with a tester present for manual login/MFA and every explicit send, offer, irreversible-action, or recovery approval.
- Keep MCP action scope narrow and preserve the browser, authorization, verified-send, evidence, and completion rules in `.trellis/spec/flyingpig/`.
- Treat unsigned macOS artifacts and manual GitHub release replacement as the accepted no-pay beta path. Publishing, signing, and notarization require a separate reviewed release task.
- Record only PII-free outcomes and blockers. Do not copy account identifiers, transaction details, private URLs, chat text, confirmation values, cookies, recordings, or local browser state.
- After the supervised smoke, decide separately whether to measure the recorded-session targets (at least 75% human escalation when an AI chatbot is detected and at least 60% goal achievement on negotiation tasks) or expand adapter coverage beyond the current supported sites.

## Acceptance Criteria

- [ ] The current desktop/helper build is running and the packaged Electron dashboard is visually checked.
- [ ] The preferred model and bounded fallback pass a harmless readiness probe without exposing page or customer data.
- [ ] A supervised smoke either completes with all authorization/checkpoint boundaries observed or records a safe, non-private blocker.
- [ ] The result is grounded in fresh visible evidence and distinguishes completed work from deferred follow-up.
- [ ] No secret, PII, browser/session state, recording, or private customer-service content is added to tracked files.
- [ ] Follow-on metrics, adapter expansion, or release work is split into separately reviewed tasks rather than silently expanded here.

## Activation Note

This task intentionally remains in `planning` and was created with `--no-start` during the Context Harness migration. Review its scope before activation; the migration must not start a live customer-service run.
