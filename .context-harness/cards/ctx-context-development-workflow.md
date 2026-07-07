---
id: ctx-context-development-workflow
kind: workflow
importance: 0.65
confidence: confirmed
source: CONTEXT.md#development-workflow
chunk: null
tokens_est: 57
tags: [context, development-workflow, workflow]
---

# CONTEXT.md: Development Workflow

## Summary
Setup: pip install -e ".[dev]" (once the project is scaffolded)

## Use when
- working on development workflow

## Key facts
- Setup: pip install -e ".[dev]" (once the project is scaffolded)
- Run: python -m flyingpig or uvicorn src.api.main:app
- Test: pytest tests/
- Lint: ruff check src/
- Format: ruff format src/

## Retrieval order
- Read `NOW.md` and concise `CONTEXT.md` as the always-read layer.
- Use this card before opening bulky `PLAN.md`, chunks, or raw source sections for this topic.
- Open raw detail only when this summary is insufficient for the task.

## Open next only if needed
- `CONTEXT.md#development-workflow`
