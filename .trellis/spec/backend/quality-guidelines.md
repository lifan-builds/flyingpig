# Backend Quality Guidelines

## Baseline

Target Python 3.12. Ruff is configured in `pyproject.toml` with a 100-column limit and `E`, `F`, `I`, `N`, `W`, and `UP` rules. Pytest uses `asyncio_mode = "auto"`; `slow` marks browser/live-style tests. Mypy is an optional dependency but has no repository command/configuration, so it is not a mandatory gate.

For normal Python changes, use the applicable safe gates from [Verification](../flyingpig/verification.md):

```bash
python3 -m ruff check src scripts tests
python3 -m pytest tests/unit -q -p no:cacheprovider
python3 -m pytest tests -q -m "not slow" -p no:cacheprovider
git diff --check
```

Add a focused test for the changed contract before relying on the broader suite.

## Test Patterns in This Repository

- Use pytest functions, `tmp_path`, and `monkeypatch` for isolated filesystem/configuration behavior. See `tests/unit/test_follow_up_reminders.py`, `tests/unit/test_config.py`, and `tests/unit/test_browser_runtime.py`.
- Use small fakes at the protocol seam instead of real model/browser services. `FakeAgentBrain` variants in `tests/unit/test_daemon_server.py`, `FakeMcpSession` in `tests/unit/test_mcp_executor.py`, and fake RPC clients in `tests/unit/test_chrome_devtools_mcp.py` are representative.
- Assert structured outputs and negative safety behavior, not only happy-path text. `tests/unit/test_run_authorization.py` checks per-target scope; `tests/unit/test_chat_workflow.py` checks fresh completion; `tests/unit/test_mcp_executor.py` checks allowlists, timeouts, stop boundaries, duplicate prevention, and privacy sentinels.
- Keep examples unmistakably synthetic (`synthetic service A`, localhost mock URLs, test-only keys) and put artifacts under temporary directories.
- Mark tests that launch browsers or require longer e2e setup as `slow`; `tests/e2e/test_mock_chat.py` demonstrates the marker even though it uses a local mock site.

## Required Review

- Ownership follows [Directory Structure](directory-structure.md); `AgentBrain` and transport handlers remain coordinators/adapters.
- Pydantic boundaries reject extra or malformed security-sensitive data; immutable plans/configuration use frozen dataclasses where appropriate.
- Async tasks, timers, subprocesses, and locks have one owner, bounded waits, cancellation cleanup, and race-focused tests.
- Authorization remains per target; exact checkpoint outbound text survives serialization; completion uses fresh evidence; graceful stop and hard cancel remain distinct.
- REST/WebSocket schemas and reconnect state are tested together when cross-layer behavior changes.
- Failures are categorized and privacy-safe; diagnostic logs are not copied into public events.
- Stored files and fixtures contain no credentials, private browser/account/session data, build output, or ignored runtime data.

## Forbidden Patterns

- Reviving `src/api/`/`src/models/` as the active product backend or inventing ORM migrations, Redis, Celery, Postgres, queues, or a second service without approved scope.
- Moving helper-owned policy into dashboard/Electron, accepting arbitrary model/tool output, broadening authorization, or bypassing verified send/checkpoints.
- Blocking the event loop with synchronous browser/MCP/process/filesystem work.
- Swallowing exceptions, cancellation, or timeout; emitting raw private errors; using unbounded retry or wait loops.
- Tests that use real accounts, customer-service chats, non-synthetic credentials, or persistent user directories.

## Gated Operations

Slow/real browser sessions, authenticated customer-service actions, `npm run desktop:dev`, helper/package builds, signing, notarization, GitHub release checks, and publishing are separately gated. Never run `npm run desktop:publish` as routine validation. A gated or skipped check is not a pass; report exactly what ran.
