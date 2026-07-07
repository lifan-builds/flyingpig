---
id: ctx-context-language
kind: language
importance: 0.82
confidence: confirmed
source: CONTEXT.md#language
chunk: .context-harness/chunks/ctx-context-language.md
tokens_est: 1767
tags: [context, language]
---

# CONTEXT.md: Language

## Summary
Hangup and Call-again: User-approved recovery when a rep gives a final refusal or a chat is dead/disconnected: end the current chat, start a fresh chat in the same browser session, and restate the current task from sc...

## Use when
- using project terms or resolving naming ambiguity
- update context terminology

## Key facts
- Hangup and Call-again: User-approved recovery when a rep gives a final refusal or a chat is dead/disconnected: end the current chat, start a fresh chat in th...
- Packaged Helper: Local browser-use runtime/daemon installed or launched for the user by the release app. Avoid: describing the release path as a script the u...
- Dashboard Control Plane: Helper-served localhost dashboard UI for goal entry, user questions, and live status. Avoid: moving browser-use planning/perception/...
- Helper-First Startup: Superseded helper/dashboard product path kept as historical language for older ADRs. Avoid: reintroducing flyingpig-helper or localhost...
- CLI-Owned Helper Lifecycle: Development-only helper lifecycle where a foreground flyingpig-helper process is stopped with Ctrl+C. Avoid: describing this as a...

## Retrieval order
- Read `NOW.md` and concise `CONTEXT.md` as the always-read layer.
- Use this card before opening bulky `PLAN.md`, chunks, or raw source sections for this topic.
- Open raw detail only when this summary is insufficient for the task.

## Open next only if needed
- `CONTEXT.md#language`
- `.context-harness/chunks/ctx-context-language.md`
