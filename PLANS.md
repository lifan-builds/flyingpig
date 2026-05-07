# Flying Pig AI (客服上树) — Initial Bootstrap

This is a living document. Keep Progress, Surprises & Discoveries,
Decision Log, and Outcomes & Retrospective up to date as work proceeds.

## Purpose / Big Picture
Build an AI agent that acts on behalf of consumers to interact with customer service chat interfaces across multiple websites (Amex, telecom, utilities, etc.). The agent will negotiate bills, resolve disputes, cancel services, and handle other customer service tasks — so users don't have to sit through hold music or argue with chatbots.

## Progress
- [x] Research existing solutions and competitors (2026-04-09)
- [x] Research browser automation frameworks (2026-04-09)
- [x] Research legal/regulatory landscape (2026-04-09)
- [x] Finalize architecture approach — Option A selected (2026-04-09)
- [x] Scaffold project structure (2026-04-09)
- [x] Implement core agent loop (LLM + browser automation) (2026-04-09)
- [x] Implement AI chatbot detection & human escalation module (2026-04-09)
- [x] Build first site adapter (Amex) (2026-04-09)
- [x] Build user dashboard (React frontend) (2026-04-10)
- [x] Implement session recording & audit trail (2026-04-10)
- [x] Add authentication & user account management (2026-04-10)
- [x] Test end-to-end flow with real chat interfaces (2026-04-10)
- [x] Deploy MVP (2026-04-10)
- [x] Add Chrome side-panel mock E2E harness (2026-05-07)

## Surprises & Discoveries
- **DoNotPay FTC fine ($193k):** Overclaiming AI capabilities has real legal consequences. Must be transparent about what the agent can and cannot do.
- **Consumer AI agents as emerging trend:** Forrester and CNBC both highlight that consumers are starting to use their own AI agents to deal with corporate chatbots — we're riding a wave.
- **Browser-Use maturity:** At 70k+ GitHub stars, browser-use is surprisingly mature for LLM-driven browser automation. Could save months vs. building from scratch.

## Decision Log

### DECIDED: Architecture Approach — Option A (2026-04-09)
Build on **browser-use** as the browser automation layer. Add site-specific adapters, customer service negotiation logic, and AI chatbot detection on top.

Rejected alternatives:
- Option B (custom Playwright) — too much reinvention
- Option C (hybrid) — unnecessary complexity at this stage; can evolve to C later if needed

### DECIDED: AI Chatbot Detection & Human Escalation (2026-04-09)
Core feature: detect when the agent is talking to an AI chatbot on the target site, and automatically attempt to escalate to a human representative. Rationale: human reps have more authority to make exceptions, approve credits, and resolve disputes — AI chatbots are typically constrained to scripted policies.

### DECIDED: Typeless Interaction (2026-04-09)
Minimize user input required. Users should be able to initiate tasks with minimal typing — e.g., selecting from common task templates, one-tap actions, or brief natural language descriptions. The agent handles all the detailed conversation.

### DECIDED: Manual Login Flow (2026-04-09)
For sites requiring auth (like Amex), the agent opens a visible browser and pauses for the user to log in manually. No credential storage, no PII risk. This is the safest approach and avoids ToS violations.

### DECIDED: Prompt Template System (2026-04-09)
Prompts stored as external .txt files in `prompts/<site>/` directory. Templates are pre-built for common tasks (fee negotiation, dispute, retention offer, general). Users select templates via CLI or API.

## Outcomes & Retrospective
(To be filled upon completion.)

## Context and Orientation
This is a greenfield project. The working directory is empty. Research has been completed and documented in FINDINGS.md. The next step is to finalize the architecture approach and scaffold the project.

## Plan of Work
1. **Design phase:** Finalize architecture, choose between Options A/B/C
2. **Scaffold:** Set up project structure, dependencies, CI
3. **Core agent:** Implement the LLM + browser automation loop
4. **First adapter:** Build Amex chat adapter as proof of concept
5. **Dashboard:** Simple React UI for users to submit tasks and view results
6. **Hardening:** Error handling, retry logic, anti-detection, audit trails
7. **MVP launch:** Deploy and test with real users

## Validation and Acceptance
- Agent can successfully open Amex chat, communicate a simple request, and report the outcome to the user
- End-to-end latency under 5 minutes for a typical interaction
- Session recording captures full conversation for user review
- No hardcoded credentials or PII in codebase
