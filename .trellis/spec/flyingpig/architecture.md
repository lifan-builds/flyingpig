# Architecture

## Product Boundary

- The Electron **Native Desktop Shell** is the only normal user-facing launch path. It owns app startup, helper supervision, window creation, retry/failure UX, packaging, and desktop update plumbing.
- The packaged Python helper owns browser-use execution, browser/CDP policy, LLM calls, prompt rendering, dashboard static hosting, reconnectable run state, pre-flight policy, reminders, and evidence/results.
- The helper-served dashboard is the **Dashboard Control Plane** and single cockpit. It owns task intake, status, decisions, notifications, and result presentation; it must not reimplement planning, browser policy, model calls, or evidence logic in frontend JavaScript.
- The **Controlled Chrome Window** is the supervised work area, not a second cockpit. The normal UX keeps the app and work window visible side by side and degrades to notification-led supervision on small screens.
- The old extension and React frontend under `docs/legacy/` are archived references. Do not add active product work there or present helper CLIs, localhost URLs, raw CDP mechanics, or legacy UIs as equivalent user paths.

## Runtime Seams

- `src/agent/` owns the model/browser loop, browser runtime, LLM runtime, user-input tools, evidence, and results.
- `src/daemon/` owns reconnectable sessions, pre-flight, transport-facing orchestration, reminders, and protocol snapshots.
- `src/sites/` owns shared adapter behavior, site profiles, registry resolution, and profile-context rendering.
- `prompts/<site>/` owns model prompt templates.
- `dashboard/` is a protocol client and presentation layer.
- `desktop/` supervises and packages the helper without absorbing Python runtime policy.

Keep `AgentBrain` a coordinator. Browser launch/profile rules, model creation/fallback, user input, prompt rendering, evidence capture, human-work semantics, and run orchestration belong in their focused modules. FastAPI and WebSocket handlers adapt transport to helper-owned state rather than hand-building run state.

## Product and Protocol Invariants

- The task brief is the source of truth. Use a small starter selector and an editable brief rather than a large grid that implies a final choice.
- The configured dashboard is a state-driven single-task assistant. Replace the primary surface across request, preparation, running, decision, and result states; keep diagnostics and operational controls progressively disclosed.
- First use is sequential: Configure, Open website, then Start. Repeat users go to the request form, while invalid saved model configuration returns fully to recovery/setup.
- The **Agent Run Plan** is the seam between daemon transport and `AgentBrain`; transport passes a prepared plan rather than constructing model/browser kwargs.
- The **Run Session** owns status, progress, pending attention, results, and reconnect snapshots. Executor progress publishes append-only into the brain-owned stream while the daemon remains the sole cursor-based broadcaster. Graceful supervisor stop and hard cancellation are distinct helper-owned lifecycle operations.
- The **Evidence Bundle** owns links among visible transcript evidence, checkpoint audit events, saved artifacts, and `TaskResult`.
- Support profiles hold declarative surface knowledge. Bespoke adapters are reserved for unusual mechanics or recovery policy.
- Deferred follow-up reminders are helper-owned durable local state, not transient dashboard-only state.
- Desktop update checking opens public release downloads for manual replacement in the unsigned beta path. Do not describe it as automatic in-place update, and do not add a separate helper self-updater.
