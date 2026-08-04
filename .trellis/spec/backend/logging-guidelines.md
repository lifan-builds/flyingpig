# Backend Logging and Public Progress

## Two Observability Channels

1. **Local diagnostics** use Python's standard `logging` package. `src/helper.py` configures level/format once; modules use `logger = logging.getLogger(__name__)`, as in `src/daemon/server.py`, `src/agent/brain.py`, and `src/agent/evidence.py`.
2. **Public run progress** is protocol data, not a mirrored log stream. `McpBrowserExecutor._run_phase()` emits fixed `progress` and `timing_span` objects; `AgentBrain` owns the append-only stream and `RunManager._drain_progress()` broadcasts it in cursor order. Follow [Supervised MCP Runtime](../flyingpig/supervised-mcp-runtime.md).

Do not install or invent a structured logging framework merely to make protocol events. Python logs may remain formatted text; public events must have explicit fields and serializers.

## Log Levels

- `DEBUG`: bounded developer diagnostics that are safe even when verbose mode is enabled. Never make secret/private payloads debug-only and assume that makes them safe.
- `INFO`: privacy-safe lifecycle milestones such as helper/client connection, run steps, browser attachment state, or artifact-save completion without the path. `src/agent/brain.py` and the WebSocket disconnect path in `src/daemon/server.py` are representative; the path-bearing calls in `src/agent/evidence.py` are privacy hotspots described below, not examples to copy.
- `WARNING`: recoverable degradation or bounded cleanup failure, such as the graceful-stop and cancellation timeouts in `RunManager`.
- `ERROR`/`logger.exception`: an operation failed and traceback context is useful, such as agent-run or browser-launch failure in `src/daemon/server.py`.

Prefer parameterized calls (`logger.info("Step %s complete", step)`) over eager interpolation. Include the component/phase and safe remediation, not an entire request object.

## Public Progress Shape

Stable MCP progress contains only type, phase, state, step, fixed message, timestamp, and optional safe `error_category`; timing adds a fixed label, duration, status, and bounded metadata. Representative implementations/tests are `McpBrowserExecutor._publish`, `RunManager._drain_progress`, `src/daemon/run_session.py::timing_span`, `tests/unit/test_mcp_executor.py`, and `tests/unit/test_daemon_server.py`.

Keep reconnect snapshots and public progress separate from diagnostic logs. The dashboard renders protocol fields and must never receive a traceback or subprocess log stream as progress.

## Privacy Exclusions

Neither logs nor public progress may contain:

- credentials, tokens, cookies, environment values, browser-profile contents, or model keys;
- prompts, model output, snapshots, tool arguments/results, raw chat/transcript text, or exact authorization target/account values;
- private URLs, executable commands/arguments, user paths, port-owner details, or unrelated process data.

`model_settings_payload()` in `src/daemon/model_settings.py` exposes only credential presence. `timing_span()` and `run_scorecard_payload()` expose coarse fields. The full policy is [Data and Privacy](../flyingpig/data-privacy.md).

Existing call sites that interpolate active URLs, user questions, checkpoint payloads, outcome JSON, or artifact paths—particularly in `src/agent/navigator.py`, `src/agent/user_input.py`, and `src/agent/evidence.py`—are compatibility/privacy hotspots. Do not copy or broaden them; scrub them when touching the surrounding behavior without weakening useful safe diagnostics.

## Review Checklist

- Is the event a local diagnostic or a public protocol event, and is it sent only on that channel?
- Are messages fixed or bounded, with no untrusted payload interpolation?
- Does each failure have a safe phase/category and one terminal state?
- Are timing/scorecard fields coarse and PII-free?
- Do synthetic tests assert that sentinel prompt/snapshot/private values are absent?
- Are skipped live/log/release inspections reported honestly rather than called passed?
