---
id: ctx-context-learned-patterns
kind: lesson
importance: 0.78
confidence: confirmed
source: CONTEXT.md#learned-patterns
chunk: .context-harness/chunks/ctx-context-learned-patterns.md
tokens_est: 1147
tags: [context, learned-patterns, lesson]
---

# CONTEXT.md: Learned Patterns

## Summary
CDP attach must reuse the current tab — when attaching via CDP, never call navigateto(newtab=True); fresh Target.createTarget lands in a new browser context and loses cookies. Use getcurrentpage() and page-level goto(...

## Use when
- avoiding repeated mistakes or applying prior corrections
- update context with durable lessons

## Key facts
- CDP attach must reuse the current tab — when attaching via CDP, never call navigateto(newtab=True); fresh Target.createTarget lands in a new browser context...
- Dashboard task URL follows the work window after CDP connects — the dashboard tab itself is never the task target. Once the work window is connected, Refresh...
- Work-window relaunch resets stale CDP pages — when reusing an already-running CDP endpoint, a Launch Work Window request must create/activate the requested t...
- CDP host/port conflicts can split loopback — if normal Chrome already owns 127.0.0.1:9222, Flying Pig Chrome may bind only [::1]:9222 and print DevTools list...
- Chrome DevTools MCP can drive existing Chrome through a minimal native backend — chrome-devtools-mcp --autoConnect can list/select/snapshot the user's existi...

## Open next
- `CONTEXT.md#learned-patterns`
- `.context-harness/chunks/ctx-context-learned-patterns.md`
