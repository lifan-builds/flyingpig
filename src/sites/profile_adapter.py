"""Shared adapter for declarative customer-service site profiles."""

from src.sites.base import BaseSiteAdapter
from src.sites.profiles import DEFAULT_ESCALATION_KEYWORDS, SiteProfile
from src.sites.prompt_renderer import render_site_prompt


class ProfileBackedAdapter(BaseSiteAdapter):
    """Adapter for known sites whose differences fit declarative guidance."""

    def __init__(self, profile: SiteProfile):
        self.profile = profile

    @property
    def name(self) -> str:
        return self.profile.name

    @property
    def chat_url(self) -> str:
        return self.profile.chat_url

    @property
    def requires_login(self) -> bool:
        return self.profile.requires_login

    def hostname_patterns(self) -> list[str]:
        return list(self.profile.hostname_patterns)

    def build_task_prompt(
        self,
        user_task: str,
        escalation_instructions: str,
        detection_instructions: str,
        template_id: str | None = None,
    ) -> str:
        return render_site_prompt(
            site=self.profile.template_site,
            base_prompt_file="base.txt",
            user_task=user_task,
            escalation_instructions=escalation_instructions,
            detection_instructions=detection_instructions,
            template_id=template_id,
            site_context=self._build_site_context(),
        )

    def get_known_escalation_keywords(self) -> list[str]:
        return self.profile.escalation_keywords or list(DEFAULT_ESCALATION_KEYWORDS)

    def _build_site_context(self) -> str:
        sections = [
            f"## Known Site Profile: {self.profile.name}",
            (
                "Use this profile as guidance after you verify the current tab is "
                f"actually on {self.profile.name} or its support surface."
            ),
        ]
        sections.extend(_format_list("Chat discovery hints", self.profile.chat_discovery_hints))
        sections.extend(_format_list("Pre-chat expectations", self.profile.pre_chat_expectations))
        sections.extend(
            _format_list(
                "Verification boundaries",
                self.profile.verification_boundaries,
            )
        )
        sections.extend(_format_list("Communication guidance", self.profile.communication_guidance))
        sections.extend(_format_list("Support notes", self.profile.support_notes))
        return "\n".join(sections).strip()


def _format_list(title: str, items: list[str]) -> list[str]:
    if not items:
        return []
    return ["", f"### {title}", *[f"- {item}" for item in items]]
