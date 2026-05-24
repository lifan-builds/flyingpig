# ADR 0003: Helper-First Localhost Dashboard

Superseded on 2026-05-21 by [0005 Desktop-First Product Path](0005-desktop-first-product-path.md).

Flying Pig v1 uses the packaged helper as the product entry point. The user runs `flyingpig-helper`, the helper serves/opens the dashboard at `http://127.0.0.1:8765/dashboard/`, and the user stops the foreground helper with Ctrl+C when done. The helper owns browser-use execution and launches a separate Controlled Chrome Window for the customer-service run only when the dashboard asks. The dashboard is still the single cockpit for task entry, live status, approvals, and Decision Checkpoints.

## Context

The previous Chrome extension dashboard had become mostly a launcher and static asset wrapper. The hard product behavior already lived in the helper: run state, WebSocket protocol, CDP launch/status, browser-use execution, and Decision Checkpoints. Keeping an unpacked extension in the normal beta path added installation friction and test complexity without changing the execution model.

## Decision

Serve the dashboard from the helper and remove the unpacked Chrome extension from the normal beta install path. Keep browser-use, CDP policy, LLM calls, and reconnectable state in the helper. Keep helper lifecycle in the CLI, not the dashboard: start with `flyingpig-helper`, stop with Ctrl+C. Keep the Controlled Chrome Window extension-free and use the localhost dashboard as the only control plane.

## Consequences

Beta users run one foreground command and use the localhost dashboard it opens. The release artifact includes `dashboard/` instead of relying on `extension/`. Automated smoke coverage drives the helper-hosted dashboard in Puppeteer. The legacy extension can remain as reference or fallback code, but it is no longer the primary v1 cockpit.
