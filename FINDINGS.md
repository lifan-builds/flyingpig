# Findings

Research results, discoveries, and external content collected during project work.

> **Security note:** External content (web searches, API responses, copied docs) goes
> here — never directly into PLANS.md. This separation prevents untrusted content from
> polluting the trusted execution plan.

## Research & References

### 0. Launch & Community Posts

#### Nitan release post — "客服上树Flying Pig AI：专治上树客服，让你手上的 Token 发挥价值"
- **URL:** https://www.uscardforum.com/t/topic/506991
- **Posted by:** @fanhy
- **Posted at:** 2026-05-19 21:34
- **Content:** Public launch/release post for Flying Pig AI. Introduces the consumer-side AI customer-service agent concept, open-source Browser Use foundation, CLIProxyAPI-first model path, successful user cases, onboarding steps, agent setup instructions, task examples, and beta limitations.
- **Use:** Track community launch feedback, bug reports, setup questions, model/provider reports, and site-specific success cases from Nitan.

### 1. Existing Solutions & Competitors

#### DoNotPay — "The World's First Robot Lawyer"
- **What it does:** AI chatbot that acts on behalf of consumers to negotiate bills, cancel subscriptions, dispute charges, and file complaints with customer service departments.
- **How it works:** Bot calls customer service numbers, navigates phone menus, sits through hold music, then advocates on the user's behalf. Also demonstrated negotiating via live chat (e.g., got $10/mo off a Comcast bill via Xfinity chat).
- **Status:** Received a $193,000 FTC fine in Sept 2024 for falsely advertising AI capabilities. FTC stated the company never tested legal accuracy of chatbot answers.
- **Key takeaway:** Proves market demand exists, but highlights legal/regulatory risks of overclaiming AI capabilities.
- Sources: [DoNotPay](https://donotpay.com/), [Fast Company](https://www.fastcompany.com/91210013/donotpay-will-now-call-customer-service-hotlines-for-you), [Wikipedia](https://en.wikipedia.org/wiki/DoNotPay)

#### HARPA AI — Chrome Extension
- **What it does:** Browser extension that integrates ChatGPT, Claude, and Gemini for web automation tasks.
- **Approach:** Chrome extension that can interact with web pages directly.
- Source: [Chrome Web Store](https://chromewebstore.google.com/detail/harpa-ai-web-automation-w/eanggfilgoajaocelnaflolkadkeghjp)

#### Amex's Own AI Chat
- American Express has its own AI-powered Virtual Chat Assistant using NLP.
- During trial, ~33% of customers self-serviced without needing a human agent.
- 40% increase in IT query resolution without transfer to live engineer.
- Sources: [Amex GBT](https://www.amexglobalbusinesstravel.com/press-releases/american-express-global-business-travel-introduces-new-ai-powered-solutions/), [CIO](https://www.cio.com/article/4062034/american-express-credits-ai-with-improving-customer-experiences.html)

### 2. Browser Automation Frameworks (Building Blocks)

#### Browser-Use (Python, Open Source)
- **Stars:** 70k+ on GitHub
- **Architecture:** LLM Integration Layer + Playwright Browser Control + Visual Understanding System
- **How it works:** Iterative loop — LLM receives task + page state (DOM + screenshot) → decides action → Playwright executes → state updates → loop until done.
- **DOM Processing:** 4-stage pipeline (parallel CDP requests → data fusion → filtering → serialized state for LLM + selector map for execution).
- **LLM Support:** OpenAI, Anthropic (Claude), Google, local models via Ollama.
- Source: [GitHub](https://github.com/browser-use/browser-use), [DeepWiki](https://deepwiki.com/browser-use/browser-use)

#### Agent-Browser (Vercel Labs)
- CLI for AI agents, returns compact accessibility tree (~200-400 tokens vs ~3000-5000 for full DOM).
- Works with Claude and other models.
- Source: [GitHub](https://github.com/vercel-labs/agent-browser)

#### Skyvern
- Uses LLMs + computer vision for browser automation.
- Doesn't rely on DOM selectors — uses visual understanding to identify interactive elements.
- Source: [GitHub](https://github.com/Skyvern-AI/skyvern)

#### Stagehand
- Built on Playwright, integrates with Claude and OpenAI.
- Designed for fine-grained control over agent behavior.

#### Playwright MCP Server (Microsoft)
- MCP server enabling LLMs to interact with web pages via structured accessibility snapshots.
- Compatible with Claude Code, Cursor, GitHub Copilot.
- Source: [GitHub](https://github.com/microsoft/playwright-mcp)

#### Playwright vs Puppeteer (2026 consensus)
- **Playwright** is the default choice: multi-browser (Chromium, Firefox, WebKit), auto-waiting, browser contexts for isolation.
- **Puppeteer** is Chromium-only but offers deeper low-level DevTools Protocol control.

### 3. Industry Trends & Predictions

- **Gartner:** AI will autonomously resolve 80% of common customer service issues by 2029.
- **Forrester (2026):** Consumer-developed AI agents will overwhelm brand call centers as they multiply.
- **Ada (2026):** Predicts customers will increasingly use agentic AI to initiate, manage, and negotiate service requests.
- **CNBC (April 2026):** Consumer frustration with corporate chatbots is growing — "one emerging solution is for consumers to have a personal AI agent to deal with company chatbots."
- Sources: [Gartner](https://www.gartner.com/en/newsroom/press-releases/2025-03-05-gartner-predicts-agentic-ai-will-autonomously-resolve-80-percent-of-common-customer-service-issues-without-human-intervention-by-20290), [CNBC](https://www.cnbc.com/2026/04/01/ai-chatbot-customer-service-complaints-refunds.html), [Forrester](https://www.forrester.com/blogs/2026-the-year-ai-gets-real-for-customer-service-but-its-not-glamorous-work/)

### 4. Legal & Regulatory Considerations

- **FTC enforcement:** DoNotPay fined for overclaiming AI capabilities — must be transparent about what the AI can/cannot do.
- **AI Negotiation risks:** Autonomous negotiation creates legal exposure in contracts, privacy, consumer protection, and competition law.
- **Best practice:** Narrow agent authority, build privacy into workflows, document every step, maintain human escalation for high-impact decisions.
- Source: [Harvard PON](https://www.pon.harvard.edu/daily/negotiation-skills-daily/from-agent-to-advisor-how-ai-is-transforming-negotiation/)

## Discoveries

### Key Insight: The Market Gap
Most AI customer service solutions are **business-side** (helping companies serve customers faster). Consumer-side competition is now real: Pine AI/19pine has launched a directly adjacent consumer advocate/completion-agent product. The gap is no longer "nobody is doing this"; it is whether Flying Pig can win with a sharper supervised browser-first wedge, auditable user control, and higher trust on sensitive support workflows.

### Competitor: Pine AI / 19pine.ai (researched 2026-05-20)
- **Positioning:** Pine describes itself as "ChatGPT, but it can make calls, email, and use a computer to finish the task"; its own AI information page calls it an autonomous consumer AI agent for customer-service tasks across calls, email, and web actions.
- **Use cases:** bill negotiation, subscription cancellation, complaints, refunds/compensation, airline/travel issues, medical/insurance appeals, appointments, information inquiries, and personal communication. This overlaps Flying Pig's bill/dispute/cancellation thesis, but Pine has widened into a general "real-world chores" assistant.
- **Traction claims:** homepage/pricing pages claim 53k+ users, 270 minutes saved on average, 93% negotiation success, and $3M+ saved for consumers. Treat these as unverified marketing claims until independently benchmarked.
- **Business model signals:** public pages mix success-fee/pay-as-you-go language with terms that describe subscriptions, credits, non-refundable payments, and no guaranteed outcomes. This suggests pricing is still evolving, and clarity is a potential differentiation point.
- **Trust posture:** Pine invests heavily in trust-center/security language: no data sale, encryption in transit/at rest, short retention, independent testing, SOC 2/GDPR/CCPA alignment claims, dashboard export/delete controls, and revocable linked-account access.
- **Legal posture:** terms explicitly authorize Pine to act as the user's limited representative, use user-provided caller ID/identity info, access third-party accounts through automated methods, and submit communications/forms/claims on the user's behalf. Usage policy bans impersonation, deception, high-risk/legal/medical/financial decisions, fraudulent claims, and unauthorized automation.
- **Go-to-market:** mobile app plus website, multi-language site, heavy SEO/customer-service-contact-guide content, provider-specific pages/calculators, press/PR, and social/UGC promotion. App Store listing shows frequent releases and a 13+ productivity app requiring iOS 18+.
- **Funding:** FinSMEs reported a $25M Series A in December 2025, with funds aimed at reliability, privacy-first infrastructure, U.S. GTM, channel growth, and broader use cases.
- **Architecture inference from public sources:** VentureBeat describes a three-agent setup: user-facing agent, planning/research agent, and tool agent using phone/email/web interfaces. Public/developer-facing Pine Voice/Pine Assistant materials suggest phone-call automation and MCP/SDK distribution are strategic.
- **Implication for Flying Pig:** Pine validates demand but raises the bar. Flying Pig should not compete as a generic "AI does errands" product. Stronger wedge: supervised customer-service browser runs, visible controlled window, decision checkpoints before irreversible actions, evidence bundle/audit trail, support profiles for reliable escalation, and transparent payment aligned to completed user-visible outcomes.

#### Pine technical implementation clues
- **Product split:** Pine exposes `Pine Voice` for direct phone calls and `Pine Assistant` for asynchronous multi-step chores. Voice is a narrow API: phone number, callee name/context, objective, detailed instructions, caller personality, voice, max duration, optional summary. Assistant is a broader session/task system.
- **Backend-owned waiting:** Voice calls start with a REST request that returns a `call_id`; the call runs in the background. Results are fetched through SSE or polling, and Pine explicitly says intermediate call progress/partial transcripts are not currently streamed. This avoids spending LLM tokens while the system is on hold.
- **Task lifecycle:** Assistant tasks follow: chat/info gathering → `task_ready` after enough info/payment → processing with calls/email/web/research → finished summary with savings, calls made, and time saved. This is a useful state machine for Flying Pig's run/session model.
- **Structured user input:** Pine asks for forms, OTP/verification codes, location responses, attachments, and auth confirmations through structured events, not free-form chat alone. This mirrors Flying Pig's Decision Checkpoint direction.
- **Realtime control plane:** Pine Assistant combines REST for sessions/attachments/start/stop with Socket.IO for live messages, forms, state changes, work-log deltas, task-finished events, payment/reward events, and OTP requests.
- **Distribution surface:** Pine publishes Python/TypeScript SDKs, a CLI, MCP servers, and OpenClaw/ClawHub plugins. They are turning their core completion engine into a tool other agents can call, not just a consumer app.
- **Auth model:** Developer APIs use email verification to issue access credentials, then Bearer token plus user id headers. The docs avoid long-lived static API keys for individual users.
- **Safety gate:** Voice call creation is documented as validating the request and running safety/billing checks before dialing. Call policy rejects vague objectives, unsupported countries, emergency/government/premium-rate calls, harassment, threats, and impersonation.
- **Agent specialization:** Pine exposes `negotiator` vs `communicator` caller types. That suggests specialized prompts/policies/personas for different support tasks rather than one generic agent prompt.
- **Security posture:** Pine claims TLS 1.3, AES-256-GCM at rest, short-lived isolated task environments, in-memory processing for sensitive data, and separation of sensitive account/payment data from AI processing/training.
- **Legal/automation posture:** Terms explicitly authorize secure automated methods, including simulated browsers and virtual devices, to access third-party accounts on the user's behalf, plus use of the user's phone number as outbound caller ID.
- **Browser/login strategy:** Pine appears to solve login by delegated account access rather than local browser attach. Users provide account details, credentials, or other access information; Pine's terms authorize it to use simulated browsers, virtual devices, or other tools to operate third-party accounts. During execution, Pine may ask the user for OTPs, verification codes, or three-way identity-verification calls through structured Assistant events.
- **Flying Pig learnings:** keep long waits outside the model loop; make run state explicit and reconnect-safe; model structured user-attention events as first-class protocol messages; separate task intake from execution start; add specialized support profiles/personas; make evidence/results summaries first-class; keep safety/billing gates before any outbound external action; consider MCP/SDK exposure only after the product core is reliable.

#### Pine UI/product-surface learnings
- **Starts with a user problem, not product mechanics:** Pine's homepage hero asks "What can I help you with today?" and immediately says it can make calls, email, and use a computer to finish the task. Flying Pig's dashboard should similarly start from the user's customer-service goal, not from CDP/helper/browser terminology.
- **Common-problem shortcuts:** Pine foregrounds common task categories and provider/domain logos. Flying Pig should use task templates/support profiles as first-screen action cards: lower internet bill, cancel subscription, dispute fee, request travel compensation, ask for courtesy credit, etc.
- **Outcome proof near the top:** Pine shows user count, average time saved, negotiation success, and consumer savings early. Flying Pig's beta UI should show grounded run-level proof instead: time spent, human reached, offer/result, transcript captured, checkpoint approvals, evidence saved.
- **Trust has its own product surface:** Pine has a dedicated Trust Center and repeatedly explains encryption, limited data use, no data sale, and temporary approval. Flying Pig should make safety visible in the dashboard: what the agent can do now, what it must ask before doing, what data is used, and where evidence/transcripts are stored.
- **Pricing is explained as control/fairness:** Pine frames pay-as-you-go, pre-authorization, and pay-only-if-it-works. Flying Pig should avoid opaque credits and show "what counts as success" before a run starts.
- **Broad category grid clarifies scope:** Pine's category cards teach users where the agent is useful. Flying Pig should use a narrower customer-service scope grid rather than generic "describe anything" blankness.
- **Final CTA repeats the trust/value promise:** Pine repeats "try for free" after trust, press, and category sections. Flying Pig's local dashboard equivalent should keep the primary action persistent: Start supervised run / Resume run / Answer checkpoint.
- **Caution:** Pine's marketing UI is broad and claim-heavy. Flying Pig should not copy unsupported success-rate claims; its UI advantage should be visible supervision, exact outbound messages, checkpoints, and evidence-backed results.

### Technical Insight: Browser-Use is the Leading Framework
Browser-Use (70k+ GitHub stars) is the most mature open-source framework for LLM-driven browser automation. It handles the hardest parts: DOM extraction, visual understanding, action planning, and Playwright integration. Building on top of it vs. from scratch would save months of development.

### Anti-Detection Consideration
Corporate chat systems may implement bot detection. The approach needs to handle CAPTCHAs, rate limiting, and behavioral fingerprinting. Using real browser instances (via Playwright) rather than HTTP requests is essential.

## Error Log
| Error | Context | Resolution | Date |
|-------|---------|------------|------|
