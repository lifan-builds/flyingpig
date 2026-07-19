# Imperative View and Rendering Guidelines

## No Framework Components

The active frontend has no framework component model or props convention. Views are semantic HTML plus small imperative render/update functions. `dashboard/index.html` provides the stable cockpit skeleton; `dashboard/dashboard.js` mutates it from helper protocol state; `desktop/status.html` and `desktop/status.js` do the same for startup diagnostics.

## Render Functions

- Give each function one visible responsibility. Examples include `renderMcpPages`, `renderTimingSpans`, `renderDecisionCheckpoint`, `renderResult`, and `renderBetaStats` in `dashboard/dashboard.js`, plus `render` in `desktop/status.js`.
- Prefer idempotent rendering: clear owned children with `replaceChildren()`, recreate the bounded list, then set visibility/classes from current state. Do not depend on stale DOM as hidden state.
- Use `document.createElement`, `append`, and `textContent` for protocol/user-derived content. The established safe pattern is:

```javascript
const item = document.createElement("li");
item.textContent = value;
list.append(item);
```

  `renderResultEvidence`, `renderMcpPages`, and `log` are representative examples. Do not replace this with dynamic `innerHTML`.
- For repeated interactive rows, construct the complete row and bind its listener where it is created, as `addAuthorizationTargetRow` and `renderDecisionCheckpoint` do. Keep serialization separate from rendering.
- Update related state affordances together. `updateReadiness`, `updateButtons`, `updateExperienceMode`, and `updateWorkflowView` are the current state-to-view boundary; avoid ad hoc class changes that bypass those functions.

## Semantic HTML and Accessibility

- Start with native elements: `main`, `header`, `section`, `details`/`summary`, `fieldset`/`legend`, `label`, `button`, `select`, `textarea`, `dl`, `ol`, and `ul`. `dashboard/index.html` is the primary example.
- Every action uses a real `button` with an explicit `type`; form controls need visible labels; decorative images use empty `alt`. Preserve `aria-live` on preparation/running views, `aria-expanded` on toggles, and meaningful `aria-label` values on grouped status/result regions.
- Reflect state through text as well as color. Existing pills, readiness labels, disabled reasons, result headings, and status diagnostics do this.
- Preserve focus-visible styling and responsive behavior in `dashboard/dashboard.css`. New dynamic controls must be keyboard reachable and have an accessible name.
- Current coverage is incomplete: there is no axe, accessibility-lint, screen-reader, or keyboard-navigation suite, and generated authorization-row labels are not fully linked with `for`/`id`. Improve these when touching the relevant view; do not claim comprehensive accessibility compliance.

## Styling

Use the existing CSS custom properties, shared control rules, state classes (`hidden`, `selected`, status classes), and media-query breakpoints in `dashboard/dashboard.css` or `desktop/status.css`. There is no CSS module, CSS-in-JS, utility framework, or build step. Prefer a reusable class over inline styles and verify narrow layouts when changing structure.

## Common Mistakes

- Injecting protocol, error, URL, checkpoint, or user text through `innerHTML`.
- Treating DOM text/classes as authoritative run state or inferring completion/authorization from what is visible.
- Adding clickable `div`/`span` elements instead of semantic controls, removing labels/focus states, or relying on color alone.
- Rewording `option.message_to_send` while rendering a checkpoint; the exact text shown must be the exact text returned on selection.
- Adding a framework/component library to solve a local imperative-view change or copying a component from `docs/legacy/`.
