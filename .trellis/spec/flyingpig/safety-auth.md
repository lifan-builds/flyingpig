# Safety and Authorization

## Authentication and Input Trust

- Authentication for customer sites is manual in a visible local browser. Never collect, persist, or delegate passwords or other credentials.
- Represent login, MFA/OTP, blocked access, and resume-after-auth as structured helper/session states and user-attention events.
- Treat scraped pages, chat messages, model responses, and tool output as untrusted input. Validate structured model output and constrain browser actions after parsing.
- Do not inspect or act on a private browser tab merely because it is technically reachable. The user must select and authorize the target surface.

## Explicit Authorization

Before any external customer-service action, the helper-owned **Pre-flight Safety Gate** validates supported scope, visible-browser permission, login expectations, evidence behavior, work-window readiness, and required checkpoints.

Consequential authorization must be structured and travel with the run:

- target account or service;
- allowed actions;
- allowed refund or payment methods;
- declined alternatives and material tradeoffs;
- Hangup and Call-again scope;
- completion criteria and expected confirmations where applicable.

A generic `user_authorized=true` value grants no permission to close, cancel, refund, accept, recover, or make another irreversible account change. A clear user task permits normal mechanics needed to pursue that task, but not an unlisted consequential action.

## Decision Checkpoints

- Use a structured **Decision Checkpoint** for offers, strategy pivots after refusal, irreversible account changes, material tradeoffs, verification boundaries, and other consequential choices.
- The model decides when a checkpoint is needed within policy; the helper and dashboard deliver it and keep it reconnect-safe. Do not create a competing frontend-only checkpoint detector.
- A checkpoint includes a type, concise summary, explicit options, one recommendation, and the exact outbound message for any option that sends one.
- Irreversible options must show the exact message before approval. The answer records the selected option id and exact approved outbound text for the audit trail.
- A checkpoint may include one model-authored neutral holding message and delay. The helper may send that exact message once to keep a live chat open, but may not improvise or confirm a consequential action.
- `ask_user` gathers missing facts; it is not a substitute for a consequential-choice checkpoint.

## Live Chat Actions and Recovery

- Customer-service sends are transactional: replace the composer draft, verify exact text, send once, confirm the message in the transcript, and suppress duplicate hashes.
- Do not expose raw fill, type, or key actions against the chat composer as an alternative send path.
- Recognize **Active Human Work** when a representative is checking or reviewing. Use a real patience window and warm acknowledgements; do not burn steps or repeatedly nudge.
- **Hangup and Call-again** is user-gated recovery after final refusal or a dead/disconnected chat. Ask first, retain the current task scope, and never restart while a human is typing or reviewing.
- Base completion on the freshest visible transcript and the authorization-specific completion checklist. Do not claim a deferred support contact or expected future event is already complete.
- Live authenticated customer-service actions require the user present for login/MFA and explicit approval moments. They are never routine test fixtures.
