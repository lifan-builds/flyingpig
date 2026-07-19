# Backend Development Guidelines

The active backend is the packaged Python helper behind the Electron desktop app. It owns supervised browser/model execution, safety policy, reconnectable run state, local persistence, evidence, and the dashboard REST/WebSocket protocol. Start with the product-wide [Flying Pig specification](../flyingpig/index.md).

`src/api/` and `src/models/` are legacy development-compatibility surfaces. They are not the backend of the normal desktop -> helper -> dashboard -> Controlled Chrome path; do not route new product work through them.

## Pre-Development Routing

1. Read [Architecture](../flyingpig/architecture.md) and identify the owning active module.
2. For browser, CDP, MCP, authorization, checkpoints, completion, stop/cancel, or progress changes, read [Browser Runtime](../flyingpig/browser-runtime.md), [Safety and Authorization](../flyingpig/safety-auth.md), and [Supervised MCP Runtime](../flyingpig/supervised-mcp-runtime.md).
3. For stored data, evidence, logs, credentials, or build artifacts, read [Data and Privacy](../flyingpig/data-privacy.md).
4. Select the local guide below, then choose checks from [Verification](../flyingpig/verification.md).

| Guide | Use it for |
|---|---|
| [Directory Structure](directory-structure.md) | Module ownership, new-file placement, Pydantic/dataclass boundaries |
| [Persistence and Local Storage](database-guidelines.md) | Process state, reminders, evidence, model settings, and the legacy SQLAlchemy surface |
| [Error Handling](error-handling.md) | Exceptions, cancellation, REST errors, WebSocket errors, safe categories |
| [Logging](logging-guidelines.md) | Python diagnostics, public progress events, and privacy exclusions |
| [Quality](quality-guidelines.md) | Ruff, pytest, synthetic fixtures, review, and gated operations |

## Quality Check

- The desktop/helper/dashboard ownership boundary remains intact; transport handlers do not absorb browser, model, evidence, or safety policy.
- Public inputs and model/tool outputs are validated; immutable plans/configuration use focused typed value objects.
- Async work has a clear owner, bounded waits, cancellation behavior, and no blocking call on the event loop.
- REST/WebSocket failures keep their existing protocol shape while exposing only actionable, privacy-safe information.
- Logs and public progress contain no secrets, prompts, snapshots, chat/account content, private URLs, user paths, or raw tool payloads.
- Tests use synthetic/local fixtures. Report live, slow, GUI, package, signing, notarization, and release checks as gated or skipped—not passed.
- No new work revives `src/api/`, `src/models/`, or an invented ORM/Redis/Celery service path.
