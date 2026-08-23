# Persistence and Local Storage

## No Active Application Database

The active packaged helper has no ORM-backed application database and no migration workflow. Its state is deliberately local and split by lifecycle. Keep persistence local to the helper and add a durable store only when a user-facing lifecycle requires it.

Read [Data and Privacy](../flyingpig/data-privacy.md) before changing any stored shape or path.

## Current Storage Map

| Data | Authority and lifetime | Existing pattern |
|---|---|---|
| Active run/session | Process-local, one helper process | Global `run_manager = RunManager()` in `src/daemon/server.py`; `RunStateStore` in `src/daemon/run_session.py` supplies reconnect snapshots but does not survive helper restart |
| Follow-up reminders | Durable user-local JSON | `FollowUpReminderStore` writes `~/.flyingpig/follow_up_reminders.json`; Pydantic validates loads, writes go to a `.tmp` sibling then `Path.replace`, and due reminders are claimed once by the helper loop |
| Run evidence/results | Local run-scoped artifacts | `EvidenceRecorder.save_session` in `src/agent/evidence.py` and `McpBrowserExecutor._save_artifact` in `src/agent/mcp_executor.py` write JSON beneath the configured `recordings`/run save directory |
| Model provider settings | Managed user-local env file | `USER_ENV_FILE` in `src/config.py` defaults to `~/.flyingpig/.env`; `src/daemon/model_settings.py` preserves unrelated lines, exposes only configured presence, and attempts mode `0600` |
| Browser login/profile state | Dedicated local browser profile | Owned by `src/agent/browser_runtime.py`; it is sensitive browser state, not evidence or application data |
| Dashboard preferences/metrics | Browser-local convenience data | Owned by `dashboard/dashboard.js`; never authoritative for run status, safety, completion, or secrets (see [Frontend State](../frontend/state-management.md)) |

## Persistence Rules

- Choose the narrowest lifetime. Keep live cursors, tasks, sockets, and run state in the owning process; persist only data that must survive restart, such as reminders, managed settings, or evidence.
- Validate JSON at load boundaries and serialize explicit shapes. `FollowUpReminder.model_validate` / `model_dump(mode="json")` and `result_ready_payload` are the local examples.
- For replaced local JSON files, preserve the reminder-store temp-write/replace pattern. Do not claim database-style transactions or multi-process locking; the current store assumes one helper owner.
- Keep paths user-local or run-scoped and create parent directories explicitly. Never check runtime files into the repository.
- Store only the minimum needed. Progress/timing/scorecard data must remain coarse and PII-free; evidence may contain authorized run content and therefore stays local and scoped.
- Secret values may be accepted by the helper settings endpoint but must not be returned. `model_settings_payload()` reports `configured` booleans, not keys.
- Tests redirect all writes to `tmp_path` and monkeypatch user-local paths. See `tests/unit/test_follow_up_reminders.py`, `tests/unit/test_config.py`, and artifact assertions in `tests/unit/test_mcp_executor.py`.

## Common Mistakes

- Treating process-local `RunStateStore` or browser `localStorage` as durable/authoritative run data.
- Persisting transcripts, private URLs, target/account values, credentials, cookies, or browser profiles in reminders, scorecards, logs, or test fixtures.
- Returning API-key values after saving them.
- Writing directly over JSON where an interrupted write could corrupt the only copy.
- Claiming durable persistence or database checks passed when the active product path did not use an application database.
