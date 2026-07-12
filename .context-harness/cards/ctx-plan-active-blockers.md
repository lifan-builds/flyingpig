---
id: ctx-plan-active-blockers
kind: plan
importance: 0.85
confidence: confirmed
source: PLAN.md#active-blockers
chunk: null
tokens_est: 186
tags: [plan, active-blockers]
---

# PLAN.md: Active Blockers

## Summary
Supervised real Amex beta smoke still needs a tester present for login/MFA and explicit send/approval moments.

## Use when
- continuing task-local active blockers

## Key facts
- Local macOS desktop artifacts are intentionally unsigned for the no-pay beta path.
- Desktop beta update checking and release verification are present; GitHub repo visibility is public.
- Published v1.0.1 is not update-checking capable because it lacks updater code/assets. v1.0.2 is the first unsigned beta update-checking baseline.
- Current Mac still has no local Developer ID Application identity, and the GitHub repo lacks signing/notarization secrets.

## Retrieval order
- Read `NOW.md` and concise `CONTEXT.md` as the always-read layer.
- Use this card before opening bulky `PLAN.md`, chunks, or raw source sections for this topic.
- Open raw detail only when this summary is insufficient for the task.

## Open next only if needed
- `PLAN.md#active-blockers`
