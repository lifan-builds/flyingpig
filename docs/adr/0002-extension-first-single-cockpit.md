# Extension-First Single Cockpit

Superseded on 2026-05-19 by [0003 Helper-First Localhost Dashboard](0003-helper-first-localhost-dashboard.md).

Flying Pig v1 uses the Chrome extension as the user entry point, but keeps browser-use execution in a packaged local helper/native host that launches a separate Controlled Chrome Window. The normal Chrome dashboard tab is the single cockpit for task entry, status, approvals, and Decision Checkpoints; the Controlled Chrome Window is only the work area that browser-use operates, launched with extensions disabled to avoid duplicate controls and page interference.

## Considered Options

- Make the terminal CLI the main product surface: rejected because users should not have to run scripts before using Flying Pig.
- Run everything inside the extension: rejected because it gives up browser-use's planning, perception, CDP recovery, and model/tool loop.
- Control the user's already-open normal Chrome tab: deferred because normal Chrome is usually not launched with a reliable automation channel.
- Put a second control surface in the Controlled Chrome Window: rejected by the Single Cockpit Rule.

## Consequences

The expected v1 layout is side-by-side: normal Chrome with the Flying Pig dashboard tab as the cockpit, and the Controlled Chrome Window as the customer-service work area. If side-by-side placement fails or the screen is small, the product keeps the same cockpit/work-area split and falls back to attention notifications.
