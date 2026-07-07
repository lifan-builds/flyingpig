---
id: ctx-context-relationships
kind: invariant
importance: 0.82
confidence: confirmed
source: CONTEXT.md#relationships
chunk: .context-harness/chunks/ctx-context-relationships.md
tokens_est: 1755
tags: [context, relationships, invariant]
---

# CONTEXT.md: Relationships

## Summary
AGENTS.md is the small activation layer; CONTEXT.md is the durable source of truth, indexed by scripts/context-index.js.

## Use when
- changing architecture or domain relationships
- update context invariants

## Key facts
- AGENTS.md is the small activation layer; CONTEXT.md is the durable source of truth, indexed by scripts/context-index.js.
- The helper-served dashboard owns interaction/status UX; the packaged helper owns browser-use execution, browser/CDP policy, LLM calls, static dashboard hosti...
- Desktop-First Product Path should hide helper, localhost, and Chrome-debugging mechanics behind the app window.
- The desktop app starts the helper and the dashboard launches a Controlled Chrome Window for v1 customer-service runs. The UX should present this as a purpose...
- When the dashboard shows Work Window Offline while the helper is online, it should expose an immediate Open Work Window action beside that status instead of...

## Retrieval order
- Read `NOW.md` and concise `CONTEXT.md` as the always-read layer.
- Use this card before opening bulky `PLAN.md`, chunks, or raw source sections for this topic.
- Open raw detail only when this summary is insufficient for the task.

## Open next only if needed
- `CONTEXT.md#relationships`
- `.context-harness/chunks/ctx-context-relationships.md`
