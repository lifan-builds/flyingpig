# Profile-Backed Site Support

Flying Pig supports most customer-service websites through a shared adapter plus declarative Support Profiles, not one bespoke adapter per site. Users prepare the chat/support surface first; the agent performs a bounded Chat Surface Check, uses profile guidance when the site is known, and falls back to generic guidance for unknown sites. Bespoke adapters are reserved for unusual mechanics or recovery policies, such as Amex's persisted scrollback and site-specific chat pacing.
