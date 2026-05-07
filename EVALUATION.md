# Evaluation & Contracts

This document contains objective grading criteria and specific verification contracts for tasks defined in `PLANS.md`. All criteria are optimized for **maximum success rate** — the primary metric is whether the agent achieves the user's desired outcome.

## Success Rate Framework

### Primary Metric: Task Completion Rate (TCR)
**Definition:** % of user-initiated tasks where the agent achieves the stated objective (bill reduced, service canceled, dispute filed, etc.)

**Target:** 70% TCR for MVP, 85%+ for production

### Success Rate Breakdown by Stage

Each interaction has multiple failure points. We measure and optimize each independently:

| Stage | Metric | Target | How to Measure |
|-------|--------|--------|----------------|
| **1. Chat Entry** | Successfully opens chat and gets into conversation | 95% | Agent reaches a message input state |
| **2. AI Detection** | Correctly identifies whether responder is AI or human | 90% | Validated against manual labeling of 100+ sessions |
| **3. Human Escalation** | Successfully reaches a human rep when AI is detected | 75% | Human rep confirms identity or demonstrates authority |
| **4. Goal Communication** | Clearly conveys user's request to the rep | 95% | Rep acknowledges and addresses the correct issue |
| **5. Negotiation Success** | Achieves a favorable outcome (discount, waiver, resolution) | 60% | Measurable outcome matches or exceeds user's ask |
| **6. Clean Exit** | Conversation ends properly, confirmation captured | 98% | Confirmation number, screenshot, or transcript saved |

### Compound Success Rate
Stages 1-4 are sequential prerequisites. The compound rate = product of all stages.
- **Minimum viable:** 95% × 90% × 75% × 95% × 60% × 98% = ~36% end-to-end
- **Optimized target:** 98% × 95% × 85% × 98% × 75% × 99% = ~58% end-to-end

## AI Chatbot Detection Criteria

The agent must detect AI chatbots using these signals:

### Detection Signals (weighted scoring)
| Signal | Weight | Description |
|--------|--------|-------------|
| **Response latency pattern** | High | AI responds in consistent <2s bursts; humans have variable 5-30s gaps |
| **Message structure** | High | AI uses templated greetings, numbered lists, disclaimers ("as an AI...") |
| **Canned response matching** | Medium | Responses match known chatbot scripts for the site |
| **Personalization depth** | Medium | AI gives generic answers; humans reference specific account details |
| **Flexibility test** | High | Ask an off-script question — AI deflects, humans engage |
| **Typing indicator behavior** | Medium | AI shows typing indicator for fixed duration; humans are variable |
| **Escalation resistance** | Low | AI repeatedly tries to resolve without transferring; humans offer options |

### Detection Accuracy Target
- **False negative (AI classified as human):** <10% — acceptable, we just negotiate with the AI
- **False positive (human classified as AI):** <5% — critical, requesting escalation from a human wastes time and goodwill

### Escalation Strategies (ordered by effectiveness)
1. **Direct request:** "I'd like to speak with a human representative please"
2. **Complexity escalation:** Introduce nuance that exceeds chatbot capabilities
3. **Keyword triggers:** Use known escalation phrases ("supervisor", "manager", "complaint")
4. **Dissatisfaction signal:** Express that the current response isn't resolving the issue
5. **Channel switch:** If chat escalation fails, suggest callback or phone

## Grading Criteria

### Functionality
- Agent navigates to target site's chat interface and initiates conversation
- Detects AI vs human responder within first 3 exchanges
- Executes appropriate escalation strategy when AI is detected
- Communicates user's request clearly and negotiates toward the goal
- Handles edge cases: chat unavailable, CAPTCHA, queue wait, agent transfer, session timeout
- Captures confirmation and full transcript

### Code Quality
- Passes ruff linting
- No inline secrets or hardcoded PII
- No generic error swallowing — all failures logged with context

### Testing
- Unit tests for AI detection signal scoring
- Unit tests for escalation strategy selection
- Integration tests for browser automation (recorded sessions)
- E2E tests against mock chat interfaces simulating AI and human responders
- Success rate regression tests — new changes must not decrease TCR

### Legal Compliance
- No overclaiming capabilities to users
- Transparent audit trail for every interaction
- User can review full transcript before any action is finalized
- Human escalation path always available for the user (not just the agent)

## Active Sprint Contracts

### Research & Architecture Decision
- **Status**: Complete (2026-04-09)

### Project Scaffold (Next)
- **Verification Method**: `pip install -e ".[dev]"` succeeds, `pytest` runs, `ruff check` passes
- **Acceptance Threshold**: Project structure matches AGENTS.md, browser-use installed and importable, basic CLI responds

### AI Detection Module
- **Verification Method**: Run detection against 20 recorded chat sessions (10 AI, 10 human)
- **Acceptance Threshold**: ≥90% correct classification, <5% false positive rate
- **Test Data**: Record real chat sessions from Amex and 2 other sites, label manually

### Human Escalation Module
- **Verification Method**: Run escalation strategies against 10 AI chatbot sessions
- **Acceptance Threshold**: ≥75% successfully reach a human rep within 5 attempts

## Evaluation Log
- 2026-04-09 - Research & Architecture - Grade: Pass - Comprehensive research completed, Option A selected.
