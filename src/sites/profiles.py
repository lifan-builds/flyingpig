"""Declarative profiles for sites that can use the shared chat adapter.

Most customer-service sites differ in discovery hints, escalation language,
and verification expectations rather than core behavior. A profile lets us add
those differences without creating a bespoke adapter module per site.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SiteProfile:
    """Configuration for a known customer-service chat site."""

    site_id: str
    name: str
    chat_url: str
    requires_login: bool
    hostname_patterns: list[str]
    login_url: str | None = None
    template_site: str = "generic"
    escalation_keywords: list[str] = field(default_factory=list)
    chat_discovery_hints: list[str] = field(default_factory=list)
    pre_chat_expectations: list[str] = field(default_factory=list)
    verification_boundaries: list[str] = field(default_factory=list)
    communication_guidance: list[str] = field(default_factory=list)
    support_notes: list[str] = field(default_factory=list)


DEFAULT_ESCALATION_KEYWORDS = [
    "supervisor",
    "manager",
    "complaint",
    "escalate",
    "human agent",
    "live agent",
    "representative",
]


AMEX_PROFILE = SiteProfile(
    site_id="amex",
    name="American Express",
    chat_url="https://www.americanexpress.com/us/customer-service/",
    login_url="https://www.americanexpress.com/en-us/account/login",
    requires_login=True,
    hostname_patterns=["americanexpress.com"],
    template_site="amex",
    escalation_keywords=[
        *DEFAULT_ESCALATION_KEYWORDS,
        "retention",
        "cancel my card",
        "close my account",
        "formal complaint",
        "human representative",
        "loyalty department",
    ],
    chat_discovery_hints=[
        "Look for a Chat button, Chat with us, or chat icon on customer service pages.",
        "Amex may show a virtual assistant before a human representative is available.",
        "The user may need to select a topic or card before chat becomes available.",
    ],
    pre_chat_expectations=[
        "The user should already be logged in before Flying Pig starts sending messages.",
        "Amex chat history may persist across sessions and cannot be cleared from the UI.",
    ],
    verification_boundaries=[
        (
            "Stop and ask_user before sharing last 4 of card, zip code, SSN, "
            "security answers, one-time codes, or other identity verification."
        ),
    ],
    communication_guidance=[
        "Be polite, warm, and firm; use loyal-cardmember framing without sounding pushy.",
        "For fee and retention tasks, ask about retention or loyalty options clearly.",
        "Always ask for a reference or confirmation number before ending a successful chat.",
    ],
    support_notes=[
        (
            "Amex chat widget scrollback is server-persisted; prior messages are "
            "read-only background unless the current task asks to reference them."
        ),
        (
            "Human chat pacing should use longer waits while a representative is "
            "reviewing instead of repeated short nudges."
        ),
    ],
)


PROFILES: dict[str, SiteProfile] = {
    "amex": AMEX_PROFILE,
    "oura": SiteProfile(
        site_id="oura",
        name="Oura Ring",
        chat_url="https://support.ouraring.com/hc/en-us/articles/360047222554-Contact-Us",
        requires_login=False,
        hostname_patterns=[
            "ouraring.com",
            "support.ouraring.com",
        ],
        escalation_keywords=[
            *DEFAULT_ESCALATION_KEYWORDS,
            "live Oura expert",
            "Oura expert",
            "member care",
            "warranty specialist",
            "replacement",
            "return or exchange",
        ],
        chat_discovery_hints=[
            "Start from the Oura Help Center Contact Us page.",
            "Look for Start a Chat, Chat, Finn, help, support, or a bottom-page chat launcher.",
            (
                "The chat may begin as a help-center widget or embedded support form "
                "rather than a full-page chat."
            ),
            (
                "If a phone scheduler appears, use chat unless the user explicitly asked "
                "for a phone appointment."
            ),
        ],
        pre_chat_expectations=[
            "Finn, Oura's virtual assistant, may ask the issue category before a human transfer.",
            (
                "Common paths include order status, return or exchange, membership, "
                "troubleshooting, warranty, and app issues."
            ),
            (
                "Pre-chat questions may ask for name, email address, order number, "
                "device/ring details, or topic."
            ),
        ],
        verification_boundaries=[
            (
                "Stop and ask_user before sharing account email, order number, serial "
                "number, shipping address, or membership details."
            ),
            (
                "Do not infer health information, symptoms, sleep data, or biometric "
                "details from the page or chat history."
            ),
            (
                "If asked to perform in-app steps or provide screenshots/logs, summarize "
                "the request and ask the user before proceeding."
            ),
        ],
        communication_guidance=[
            (
                "Use Oura customer language: member, Oura Ring, Oura App, membership, "
                "order, replacement, return, warranty."
            ),
            (
                "For hardware issues, be precise about the symptom, ring generation, "
                "charger, battery, firmware, and troubleshooting already tried when the "
                "user provides those facts."
            ),
            (
                "For refunds, returns, warranty, or membership billing, state the desired "
                "remedy plainly and ask for confirmation of the next step."
            ),
        ],
        support_notes=[
            "Oura chat is available 24/7.",
            (
                "Chat starts with Finn, the virtual assistant, and can transfer to a live "
                "Oura expert if needed."
            ),
            (
                "When an Oura expert says they are checking, reviewing account details, "
                "or need a moment, wait patiently and use friendly acknowledgements "
                "before sending another prompt or summarizing the result."
            ),
            (
                "Oura also offers scheduled phone support, but chat should remain the "
                "default path for this adapter."
            ),
        ],
    ),
}


PROFILE_TEMPLATE_FALLBACKS: dict[str, str] = {
    profile.site_id: profile.template_site
    for profile in PROFILES.values()
    if profile.template_site != profile.site_id
}
