---
id: ctx-plan-findings
kind: plan
importance: 0.85
confidence: confirmed
source: PLAN.md#findings
chunk: .context-harness/chunks/ctx-plan-findings.md
tokens_est: 10671
tags: [plan, findings, 2026-07-12-amex-session-hardening-implementation, 2026-07-05-installed-work-window-cdp-conflict, 2026-07-05-chrome-devtools-mcp-auto-connect, 2026-05-25-public-beta-first-run-readiness, 2026-05-05-amex-live-flow-handoff, 2026-05-06-mock-amex-system-chrome-run, 2026-05-06-live-amex-oura-cdp-run, 2026-05-06-live-amex-oura-task-handoff, 2026-05-06-live-amex-oura-71009-run, 2026-05-06-live-run-observations-and-improvements, 2026-05-06-architecture-deepening, 2026-05-12-oura-supervised-run-and-pacing-findings, 2026-05-15-extension-first-beta-release-evidence, 2026-05-19-helper-first-dashboard-and-external-chat-surface-smoke, 2026-05-20-dashboard-huca-restart-control, 2026-05-21-pine-informed-protocol-hardening, 2026-05-21-architecture-deepening-follow-up, 2026-05-21-desktop-first-product-path-cleanup, 2026-05-23-run-readiness-and-speed-dashboard, 2026-05-24-release-1-0-0-preparation, 2026-05-24-release-1-0-1-publishing-pass, 2026-05-25-local-scorecards-and-desktop-update-foundation, 2026-05-25-auto-update-release-hardening]
---

# PLAN.md: Findings

## Summary
See archived FINDINGS.md (if retained) for research on DoNotPay, browser-use, Playwright vs Puppeteer, FTC/legal landscape, and industry predictions (Gartner/Forrester/CNBC 2026).

## Use when
- continuing task-local findings

## Key facts
- Added RunAuthorization and carried explicit target/action/refund/declined-alternative/HUCA scope through REST, daemon orchestration, AgentBrain,...
- Added transcript-derived chat workflow state for human handoff/activity, cancellation disclosure and consent, closure confirmation,...
- Added semantic sendchatmessage with exact composer replacement, draft verification, one send, transcript verification, and duplicate suppression;...
- Added MCP active-human waits, one bounded warm holding message, bounded model calls, fallback planning, trailing-JSON recovery, textless internal waits,...
- Added CLIProxy model listing/probing with candidate preference gpt-5.6-luna, gpt-5.4-mini, configured preference, gpt-5.5, then gpt-5.4;...

## Retrieval order
- Read `NOW.md` and concise `CONTEXT.md` as the always-read layer.
- Use this card before opening bulky `PLAN.md`, chunks, or raw source sections for this topic.
- Open raw detail only when this summary is insufficient for the task.

## Open next only if needed
- `PLAN.md#findings`
- `.context-harness/chunks/ctx-plan-findings.md`
