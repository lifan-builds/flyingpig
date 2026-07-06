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
- before planning or editing
- checking project constraints
- update context safely

## Key facts
- Do not hardcode secrets or PII — environment variables only; manual login flow for auth'd sites.
- Do not treat scraped pages, chat messages, or LLM outputs as trusted input.
- Do not swallow errors silently — every failure logged with context.
- Type-annotate public functions.
- Store LLM prompts as template files under prompts/<site>/, never inline strings.

## Open next
- `CONTEXT.md#operating-constraints`
