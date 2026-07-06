---
id: ctx-plan-findings
kind: plan
importance: 0.85
confidence: confirmed
source: PLAN.md#findings
chunk: .context-harness/chunks/ctx-plan-findings.md
tokens_est: 9896
tags: [plan, findings, 2026-07-05-installed-work-window-cdp-conflict, 2026-07-05-chrome-devtools-mcp-auto-connect, 2026-05-25-public-beta-first-run-readiness, 2026-05-05-amex-live-flow-handoff, 2026-05-06-mock-amex-system-chrome-run, 2026-05-06-live-amex-oura-cdp-run, 2026-05-06-live-amex-oura-task-handoff, 2026-05-06-live-amex-oura-71009-run, 2026-05-06-live-run-observations-and-improvements, 2026-05-06-architecture-deepening, 2026-05-12-oura-supervised-run-and-pacing-findings, 2026-05-15-extension-first-beta-release-evidence, 2026-05-19-helper-first-dashboard-and-external-chat-surface-smoke, 2026-05-20-dashboard-huca-restart-control, 2026-05-21-pine-informed-protocol-hardening, 2026-05-21-architecture-deepening-follow-up, 2026-05-21-desktop-first-product-path-cleanup, 2026-05-23-run-readiness-and-speed-dashboard, 2026-05-24-release-1-0-0-preparation, 2026-05-24-release-1-0-1-publishing-pass, 2026-05-25-local-scorecards-and-desktop-update-foundation, 2026-05-25-auto-update-release-hardening]
---

# PLAN.md: Findings

## Summary
See archived FINDINGS.md (if retained) for research on DoNotPay, browser-use, Playwright vs Puppeteer, FTC/legal landscape, and industry predictions (Gartner/Forrester/CNBC 2026).

## Use when
- continuing the active task
- checking done criteria or decisions
- update context with task-local progress

## Key facts
- See archived FINDINGS.md (if retained) for research on DoNotPay, browser-use, Playwright vs Puppeteer, FTC/legal landscape, and industry predictions (Gartner...
- The running desktop app is the packaged local build at dist/desktop/mac-arm64/Flying Pig.app; no /Applications/Flying Pig.app install was found in this session.
- The helper is healthy on 127.0.0.1:8765, but Open Work Window fails because normal Chrome owns IPv4 127.0.0.1:9222 and returns 404 for /json/version, while t...
- The helper/dashboard status path collapses any cdpurl to http://127.0.0.1:<port> and therefore reports Work Window Offline even when http://localhost:9222/js...
- Direct Chrome debugging is viable: launching Chrome with a separate profile and --remote-debugging-address=127.0.0.1 --remote-debugging-port=9335 produced a...

## Open next
- `PLAN.md#findings`
- `.context-harness/chunks/ctx-plan-findings.md`
