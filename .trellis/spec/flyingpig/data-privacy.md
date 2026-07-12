# Data and Privacy

## Secrets and Sensitive State

- Never hardcode or commit credentials, API keys, tokens, cookies, browser profiles, chat/account details, or other PII. Supply secrets through environment variables or user-local files whose values are not logged or copied into evidence.
- Keep ignored/runtime state out of migration and product diffs: `.env`, `.playwright-mcp/`, `recordings/`, database files, `~/.flyingpig`, browser profiles/session state, caches, `node_modules/`, `build/`, `dist/`, generated packages, signing/notarization material, and `.DS_Store`.
- Do not print ignored values during diagnostics. Record only safe presence, shape, status, or redacted counts.

## Evidence, Logs, and Metrics

- Failures must be logged with actionable context, but context must not include secret or private payloads.
- An **Evidence Bundle** may link browser-use history, visible transcript evidence, checkpoint audit events, and the final result. Access and retention remain local and scoped to the authorized run.
- **Run Timing Spans** contain phase, duration, and safe status only. Never include raw chat text, private URLs, credentials, or account details.
- **Run Scorecards** may contain coarse outcome fields such as status, site/profile class, goal type, human reached, HUCA/checkpoint/intervention counts, durations, offer/result presence, unresolved-item count, blocked reason, and user-confirmed outcome. They must not contain transcripts, private URLs, cookies, credentials, account details, or chat logs.
- **First-run Activation Signals** are local, coarse, and PII-free. Do not turn them into cloud telemetry without explicit approval.
- Deferred reminder records hold only the minimum structured follow-up data needed for local delivery. Do not misrepresent an unresolved future action as completed work.

## Releases and Updates

- Before publishing any release artifact, scan it for PII, API keys, credentials, tokens, cookies, logs, recordings, user-specific account information, database files, browser state, and private build inputs.
- Signing, notarization, packaging, and publishing are explicit release operations. They are not default development or migration validation.
- Public update checks must not embed a private repository token or other credential.

## Review Rule

Review every changed and staged path and relevant content; do not rely only on ignore rules or a diff summary. Examples and test fixtures must use unmistakably synthetic values.
