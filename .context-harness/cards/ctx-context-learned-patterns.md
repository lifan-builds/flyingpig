---
id: ctx-context-learned-patterns
kind: lesson
importance: 0.78
confidence: confirmed
source: CONTEXT.md#learned-patterns
chunk: .context-harness/chunks/ctx-context-learned-patterns.md
tokens_est: 1669
tags: [context, learned-patterns, lesson]
---

# CONTEXT.md: Learned Patterns

## Summary
CDP attach must reuse the current tab — when attaching via CDP, never call navigateto(newtab=True); fresh Target.createTarget lands in a new browser context and loses cookies.

## Use when
- avoiding a repeated failure or applying a durable correction

## Key facts
- Dashboard task URL follows the work window after CDP connects — the dashboard tab itself is never the task target.
- Work-window relaunch resets stale CDP pages — when reusing an already-running CDP endpoint, a Launch Work Window request must create/activate the requested...
- CDP host/port conflicts can split loopback — if normal Chrome already owns 127.0.0.1:9222, Flying Pig Chrome may bind only [::1]:9222 and print DevTools...
- Chrome DevTools MCP can drive existing Chrome through a minimal native backend — chrome-devtools-mcp --autoConnect can list/select/snapshot the user's...
- browser-use page wrappers are not Playwright pages — use await page.geturl(), await page.gettitle(), and await page.goto(url);...

## Retrieval order
- Read `NOW.md` and concise `CONTEXT.md` as the always-read layer.
- Use this card before opening bulky `PLAN.md`, chunks, or raw source sections for this topic.
- Open raw detail only when this summary is insufficient for the task.

## Open next only if needed
- `CONTEXT.md#learned-patterns`
- `.context-harness/chunks/ctx-context-learned-patterns.md`
