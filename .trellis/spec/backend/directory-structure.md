# Backend Directory Structure

## Active Product Boundary

The normal path is Electron -> packaged `src.helper` process -> helper-served dashboard -> supervised Controlled Chrome/CDP/MCP runtime. Detailed ownership lives in [Architecture](../flyingpig/architecture.md); this guide answers where Python changes belong.

```text
src/
├── helper.py                 # development/packaged helper entry point
├── config.py                 # Pydantic settings and user-local env location
├── agent/                    # model/browser loop and focused runtime policy
│   ├── brain.py              # coordinator, not a policy grab bag
│   ├── browser_runtime.py    # Chrome launch/profile/CDP mechanics
│   ├── mcp_executor.py       # bounded MCP observe/action executor
│   ├── run_authorization.py  # authoritative authorization models
│   ├── run_orchestration.py  # normalized AgentRunPlan seam
│   ├── evidence.py           # artifacts and result serialization
│   └── ...                   # checkpoints, user input, LLM, human-work logic
├── daemon/                   # reconnectable helper service and transport
│   ├── server.py             # FastAPI/WebSocket adapters and RunManager
│   ├── run_session.py        # protocol states/events and snapshots
│   ├── preflight.py          # helper-owned run-start safety gate
│   ├── follow_up_reminders.py
│   └── model_settings.py
└── sites/                    # adapter interface, profiles, registry, prompts
```

Long prompts stay under `prompts/<site>/`; tests mirror behavior under `tests/unit/`, `tests/integration/`, and gated `tests/e2e/`.

## Responsibility-Based Modules

- Keep `AgentBrain` in `src/agent/brain.py` as a coordinator. Put browser/profile behavior in `browser_runtime.py`, model construction/fallback in `llm_runtime.py`, user-attention tools in `user_input.py` and `decision_checkpoint.py`, evidence/results in `evidence.py` and `result.py`, and run normalization in `run_orchestration.py`.
- Put reconnectable session state and transport-facing orchestration in `src/daemon/`. `RunManager` in `src/daemon/server.py` owns one active run and adapts it to REST/WebSocket; `RunStateStore` in `src/daemon/run_session.py` owns the reconnect snapshot.
- Put normal site variation in immutable `SiteProfile` values in `src/sites/profiles.py` and `ProfileBackedAdapter` in `src/sites/profile_adapter.py`. Add a bespoke `BaseSiteAdapter` subclass only for unusual mechanics or recovery policy; see `src/sites/amex.py` and `src/sites/generic.py`.
- Keep synchronous OS/process/CDP bridges out of the event loop. Existing transport examples use `asyncio.to_thread(...)` in `src/daemon/server.py`; bounded MCP phases live in `McpBrowserExecutor._run_phase`.

## Boundary Types

- Use Pydantic models where untrusted or serialized data enters the helper: REST request models in `src/daemon/server.py`, strict `AuthorizationTarget`/`RunAuthorization` in `src/agent/run_authorization.py`, `McpAgentAction` in `src/agent/mcp_executor.py`, and `FollowUpReminder` in `src/daemon/follow_up_reminders.py`.
- Use `@dataclass(frozen=True)` for immutable internal plans/configuration/value objects: `AgentRunPlan`, `PreflightResult`, `ChromeLaunchConfig`, `SessionArtifacts`, `SiteProfile`, and `ChromeMcpPage` are representative examples.
- Mutable lifecycle objects are deliberate exceptions. `TaskResult` accumulates evidence/timing, while `RunManager` and `RunStateStore` own changing run state; do not mark stateful owners frozen merely for uniformity.
- Public and changed functions should carry useful type annotations and stay small enough to expose ownership. Follow [Coding](../flyingpig/coding.md) for the cross-layer contract.

## Naming and Placement

Use lowercase `snake_case.py` modules, `PascalCase` classes/Pydantic models/dataclasses, `snake_case` functions and fields, and `UPPER_SNAKE_CASE` constants. Name protocol values explicitly (`RunStatus`, `RunEventType`, `TaskStatus`) rather than scattering anonymous strings.

## Boundary Guardrails and Common Mistakes

Do not:

- create a second backend, ORM, queue, or framework layer without an approved product need;
- move helper safety, authorization, completion, browser, or model policy into dashboard JavaScript or Electron;
- grow `src/daemon/server.py` or `AgentBrain` with logic already owned by a focused module;
- block async loops with subprocess, filesystem, MCP, or CDP work that should be delegated and bounded.
