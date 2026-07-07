---
id: ctx-context-workflow
kind: workflow
importance: 0.9
confidence: confirmed
source: CONTEXT.md#workflow
chunk: null
tokens_est: 129
tags: [context, workflow, verification]
---

# CONTEXT.md: Workflow

## Summary
Setup: pip install -e ".[dev]"

## Use when
- running, testing, linting, deploying, deployment, or verifying changes

## Key facts
- Setup: pip install -e ".[dev]"
- Run product app: npm run desktop:dev
- Build helper sidecar: npm run build:helper
- Package desktop app: npm run desktop:package
- Publish desktop update artifacts: npm run desktop:publish

## Retrieval order
- Read `NOW.md` and concise `CONTEXT.md` as the always-read layer.
- Use this card before opening bulky `PLAN.md`, chunks, or raw source sections for this topic.
- Open raw detail only when this summary is insufficient for the task.

## Open next only if needed
- `CONTEXT.md#workflow`
