---
id: ctx-context-operating-constraints
kind: constraints
importance: 0.9
confidence: confirmed
source: CONTEXT.md#operating-constraints
chunk: null
tokens_est: 257
tags: [context, operating-constraints, constraints]
---

# CONTEXT.md: Operating Constraints

## Summary
Do not hardcode secrets or PII — environment variables only; manual login flow for auth'd sites.

## Use when
- before choosing an implementation or changing project behavior

## Key facts
- Do not treat scraped pages, chat messages, or LLM outputs as trusted input.
- Do not swallow errors silently — every failure logged with context.
- Type-annotate public functions.
- Store LLM prompts as template files under prompts/<site>/, never inline strings.
- Have site adapters inherit from BaseSiteAdapter and implement its interface.

## Retrieval order
- Read `NOW.md` and concise `CONTEXT.md` as the always-read layer.
- Use this card before opening bulky `PLAN.md`, chunks, or raw source sections for this topic.
- Open raw detail only when this summary is insufficient for the task.

## Open next only if needed
- `CONTEXT.md#operating-constraints`
