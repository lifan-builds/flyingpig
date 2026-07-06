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

## Open next
- `CONTEXT.md#coding-conventions`
