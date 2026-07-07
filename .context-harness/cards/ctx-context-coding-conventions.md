---
id: ctx-context-coding-conventions
kind: context
importance: 0.65
confidence: confirmed
source: CONTEXT.md#coding-conventions
chunk: null
tokens_est: 91
tags: [context, coding-conventions]
---

# CONTEXT.md: Coding Conventions

## Summary
Type hints on all public functions

## Use when
- working on coding conventions

## Key facts
- Type hints on all public functions
- Async-first for browser and API operations
- Site adapters inherit from BaseSiteAdapter and implement a standard interface
- LLM prompts stored as separate template files, not inline strings
- Secrets via environment variables, never hardcoded

## Retrieval order
- Read `NOW.md` and concise `CONTEXT.md` as the always-read layer.
- Use this card before opening bulky `PLAN.md`, chunks, or raw source sections for this topic.
- Open raw detail only when this summary is insufficient for the task.

## Open next only if needed
- `CONTEXT.md#coding-conventions`
