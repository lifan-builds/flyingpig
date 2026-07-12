# Browser Runtime

## Controlled Chrome and Prepared Surfaces

- The **Controlled Chrome Window** is the helper-launched visible browser that the runtime may attach to over CDP. It is a supervised work area, not the dashboard.
- Prefer a persistent **Dedicated Work Profile** for first-run beta use. It may retain login state and must have an explicit reset path; it is not incognito.
- An advanced user-profile path may use an explicit profile directory, but current Chrome blocks remote debugging against the literal default profile. Fail clearly instead of promising direct default-profile CDP control.
- Disable extensions in the Controlled Chrome Window for the v1 path to reduce interference and duplicate controls.
- A **User-Prepared Chat Surface** is a user-selected tab already navigated and logged in as needed with a plausible support entry point visible.
- Perform one bounded **Chat Surface Check** for an existing input or obvious launcher. Do not roam from a site homepage to discover support.

## CDP Invariants

- CDP attach reuses the current tab and browser context. Do not create a new tab/context that loses cookies; use browser-use page-wrapper methods such as `get_current_page()`, `get_url()`, `get_title()`, and `goto()` rather than Playwright-only properties or arguments.
- The dashboard tab is never the task target. After work-window connection, Refresh and Start derive the target from the debuggable work-window page.
- Relaunching a reused endpoint must activate/create the requested task page and remove stale page targets so an old tab cannot silently become the next target.
- Preserve the requested CDP host, including `localhost`, IPv4, or IPv6. Do not collapse every endpoint to `127.0.0.1`; host/port conflicts can split loopback listeners.

## Chrome DevTools MCP

- MCP auto-connect can inspect a user-authorized existing Chrome tab when Chrome remote-debugging permission is enabled. Treat this as sensitive real-browser access.
- Keep one helper-owned MCP process alive where practical because Chrome may require visible approval per process.
- Keep the MCP action allowlist narrow and prefer local/mock validation before any authenticated use.
- Selected MCP tabs are runnable only through the explicit MCP backend contract. Do not claim browser-use/CDP readiness when no compatible CDP handoff exists.
- Planner calls are bounded. List and harmlessly probe local model candidates before sending page data, skip quota-blocked or stalled candidates, and retain a bounded fallback.
- Structured action parsing may retry once without provider schema enforcement and decode only the first complete JSON object. Parsing recovery never bypasses action allowlists, authorization, or checkpoints.
- MCP chat writes use the same semantic verified-send operation as other backends; direct composer fill/type/key actions remain forbidden.

## Supervision

Use dashboard REST/WebSocket paths for live runs so questions and checkpoints can resume the same run. Do not launch a live customer-service session from an unattended background CLI that cannot receive user input.
