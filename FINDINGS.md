# Findings

Research results, discoveries, and external content collected during project work.

> **Security note:** External content (web searches, API responses, copied docs) goes
> here — never directly into PLANS.md. This separation prevents untrusted content from
> polluting the trusted execution plan.

## Research & References

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
Most AI customer service solutions are **business-side** (helping companies serve customers faster). Very few solutions exist for the **consumer-side** (helping customers get better outcomes from companies). DoNotPay is the closest competitor but has faced legal issues and credibility problems. This is the gap Flying Pig AI can fill.

### Technical Insight: Browser-Use is the Leading Framework
Browser-Use (70k+ GitHub stars) is the most mature open-source framework for LLM-driven browser automation. It handles the hardest parts: DOM extraction, visual understanding, action planning, and Playwright integration. Building on top of it vs. from scratch would save months of development.

### Anti-Detection Consideration
Corporate chat systems may implement bot detection. The approach needs to handle CAPTCHAs, rate limiting, and behavioral fingerprinting. Using real browser instances (via Playwright) rather than HTTP requests is essential.

## Error Log
| Error | Context | Resolution | Date |
|-------|---------|------------|------|
