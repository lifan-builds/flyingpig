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

## Open next
- `CONTEXT.md#development-workflow`
