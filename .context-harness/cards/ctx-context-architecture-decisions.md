---
id: ctx-context-architecture-decisions
kind: context
importance: 0.65
confidence: confirmed
source: CONTEXT.md#architecture-decisions
chunk: null
tokens_est: 203
tags: [context, architecture-decisions]
---

# CONTEXT.md: Architecture Decisions

## Summary
2026-04-09: Chose Playwright over Puppeteer — multi-browser support, auto-waiting, better ecosystem for AI agents in 2026.

## Use when
- working on architecture decisions

## Key facts
- 2026-04-09: Option A selected — build on browser-use framework (70k+ stars). Handles DOM extraction, visual understanding, and action planning.
- 2026-04-09: Consumer-side positioning (agent acts for the user, not the company) — this is the market gap.
- 2026-04-09: AI chatbot detection is a core feature. When the target site uses an AI chatbot, the agent automatically attempts to escalate to a human rep...
- 2026-04-09: Typeless interaction — minimize user input. Users pick from task templates or give brief descriptions; the agent handles all detailed conversation.

## Retrieval order
- Read `NOW.md` and concise `CONTEXT.md` as the always-read layer.
- Use this card before opening bulky `PLAN.md`, chunks, or raw source sections for this topic.
- Open raw detail only when this summary is insufficient for the task.

## Open next only if needed
- `CONTEXT.md#architecture-decisions`
