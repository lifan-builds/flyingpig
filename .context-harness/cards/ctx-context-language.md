---
id: ctx-context-language
kind: language
importance: 0.82
confidence: confirmed
source: CONTEXT.md#language
chunk: .context-harness/chunks/ctx-context-language.md
tokens_est: 1842
tags: [context, language]
---

# CONTEXT.md: Language

## Summary
Hangup and Call-again: User-approved recovery when a rep gives a final refusal or a chat is dead/disconnected: end the current chat, start a fresh chat in the same browser session,...

## Use when
- using canonical project terms or resolving naming ambiguity

## Key facts
- Packaged Helper: Local browser-use runtime/daemon installed or launched for the user by the release app.
- Dashboard Control Plane: Helper-served localhost dashboard UI for goal entry, user questions, and live status.
- Helper-First Startup: Superseded helper/dashboard product path kept as historical language for older ADRs.
- CLI-Owned Helper Lifecycle: Development-only helper lifecycle where a foreground flyingpig-helper process is stopped with Ctrl+C.
- Hybrid Helper Startup: Superseded beta path where a login/background helper service could start before a packaged app.

## Retrieval order
- Read `NOW.md` and concise `CONTEXT.md` as the always-read layer.
- Use this card before opening bulky `PLAN.md`, chunks, or raw source sections for this topic.
- Open raw detail only when this summary is insufficient for the task.

## Open next only if needed
- `CONTEXT.md#language`
- `.context-harness/chunks/ctx-context-language.md`
