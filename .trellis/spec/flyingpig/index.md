# Flying Pig Specifications

Flying Pig is a supervised, consumer-side customer-service automation product. The normal product path is the Electron desktop app; its packaged Python helper owns browser, model, run-state, and evidence behavior, while the helper-served dashboard is the cockpit UI.

## Pre-Development Checklist

1. Classify the changed surface using [Architecture](architecture.md).
2. For any action that can affect an account, payment, refund, cancellation, live chat, or browser session, read [Safety and Authorization](safety-auth.md).
3. For Chrome, CDP, MCP, tabs, profiles, chat surfaces, or model-driven browser actions, read [Browser Runtime](browser-runtime.md).
4. For supervised MCP progress, target authorization, completion, duplicate prevention, stop semantics, or build/startup diagnostics, read [Supervised MCP Runtime Contract](supervised-mcp-runtime.md).
5. For local state, evidence, logs, metrics, release artifacts, or user data, read [Data and Privacy](data-privacy.md).
6. Apply [Coding](coding.md) to Python, JavaScript, adapters, prompts, and error handling.
7. Select checks from [Verification](verification.md); live authenticated and release operations are gated separately.

## Topics

- [Architecture](architecture.md) — current product path and module ownership.
- [Safety and Authorization](safety-auth.md) — manual login, explicit action scope, checkpoints, HUCA, and untrusted input.
- [Browser Runtime](browser-runtime.md) — Controlled Chrome, CDP/profile/tab rules, prepared chat surfaces, and MCP limits.
- [Supervised MCP Runtime Contract](supervised-mcp-runtime.md) — live progress, target authorization, fresh completion, duplicate guards, stop/cancel semantics, and build/startup diagnostics.
- [Data and Privacy](data-privacy.md) — secrets, PII, evidence, metrics, local state, and release exclusions.
- [Coding](coding.md) — typing, async boundaries, adapters, prompts, and failures.
- [Verification](verification.md) — safe lint, tests, smokes, syntax checks, and gated probes.

Historical product paths and decisions remain in `docs/adr/`, `docs/legacy/`, and other repository-owned product documents. They are evidence, not permission to revive a superseded path.

## Quality Check

- Confirm the desktop/helper/dashboard ownership boundary still holds.
- Confirm consequential actions have explicit structured authorization and checkpoint behavior.
- Confirm scraped pages, chat text, and model output remain untrusted.
- For supervised MCP changes, trace the complete [Supervised MCP Runtime Contract](supervised-mcp-runtime.md) across executor, brain, daemon, dashboard, helper health, and desktop startup.
- Confirm changed data, logs, metrics, evidence, and artifacts contain no secrets or private account/session material.
- Run all applicable commands in [Verification](verification.md) and report gated or skipped checks honestly.
- Run `python3 ./.trellis/scripts/get_context.py --mode packages` and verify that `flyingpig` is listed.
