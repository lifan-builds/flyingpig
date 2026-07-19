# Frontend State Management

## No State Library

The dashboard uses one mutable page-local `state` object in `dashboard/dashboard.js`, browser-local preference helpers, and helper-authoritative REST/WebSocket state. Electron uses small module-local lifecycle variables in `desktop/main.js` and instance state in `desktop/helper_supervisor.js`. There is no Redux, Pinia, Zustand, React context, query cache, or client-side model store.

## Three State Categories

### 1. Ephemeral view and connection state

Keep sockets, connection flags, selected/active page metadata, busy flags, timers, open panels, notification deduplication keys, and the currently rendered result/checkpoint in the page-local `state` object. Examples are `socket`, `connected`, `browserStatusTimer`, `currentCheckpoint`, `settingsOpen`, and `activityOpen`. Derive controls through `updateButtons`, `updateReadiness`, and `updateWorkflowView` rather than persisting every visual flag.

### 2. User-local preferences and convenience history

`storageGet`/`storageSet` use extension storage when available and otherwise JSON values under `flyingpig.*` in `localStorage`. Current values include helper/CDP URL, model choice, task draft, notification choices, Chrome profile, selected site, authorization form selections, activation signals, and up to 50 coarse beta scorecards.

Treat these values as untrusted input restoration, not server state. Current compatibility keys include `activeUrl` and authorization target displays, so browser storage is sensitive local data even though it is not authoritative; do not copy those values into logs, metrics, notifications, or cloud state, and do not broaden what is retained. Never store API-key values, transcripts, cookies, browser-profile contents, raw protocol/log payloads, or evidence there. Model keys go to the helper-managed user env file; the UI retains only provider choice and configured/not-configured status. Follow [Data and Privacy](../flyingpig/data-privacy.md).

### 3. Helper-authoritative run, safety, and result state

The Python helper owns active run status, pending attention, pre-flight failures, authorization validation, progress/timing order, stop/cancel semantics, reminders, completion, scorecards/results, and evidence. `connectHelper` applies `type="state"` reconnect snapshots through `setRunState`; REST endpoints provide helper health, model settings, browser state, and reminders. The UI may render or submit requests, but must not infer that a run is authorized, complete, successful, or safely stopped from local state.

## Authorization and Checkpoint Invariants

- Preserve per-target authorization. `authorizationTargetValues` reads each row's own checkboxes; `runAuthorizationPayload` maps each non-empty row to its own `target-N` and `authorized_actions`. Never derive every row's permissions from aggregate controls or reuse one target's actions for another.
- Persisted authorization form choices only prefill the next request. Python `AuthorizationTarget`/`RunAuthorization` validation and helper pre-flight remain authoritative; `user_authorized: true` by itself grants no consequential action. See [Safety and Authorization](../flyingpig/safety-auth.md).
- Preserve exact checkpoint text. `renderDecisionCheckpoint` displays `option.message_to_send`; `checkpointOptionAnswer` returns it unchanged as `selected_message`:

```javascript
return {
  checkpoint_id: checkpoint.checkpoint_id,
  selected_option_id: option.id,
  selected_message: option.message_to_send || null,
};
```

  Do not trim, summarize, translate, reconstruct, or replace that message between display and answer serialization. Custom instructions use `selected_message: null` plus `free_text`.
- Keep graceful stop (`type: "stop"`) distinct from hard cancel (`type: "cancel"`) and HUCA replacement. The dashboard's “Stop safely” path requests helper-owned fresh-evidence evaluation; it does not locally mark the run cancelled or successful.

## Common Mistakes

- Treating `localStorage`, DOM state, activation signals, or local scorecards as authoritative run/safety/result data.
- Mutating state without calling the established derived render/update functions, leaving readiness and controls inconsistent.
- Reconstructing pending attention after reconnect instead of rendering the helper snapshot.
- Broadening target permissions, turning generic authorization into an action grant, or dropping exact checkpoint outbound text.
- Adding a global state framework or cloud synchronization for the existing single-page local cockpit without approved scope.
