"""Shared adapter for declarative customer-service site profiles."""

from src.sites.base import BaseSiteAdapter
from src.sites.profiles import DEFAULT_ESCALATION_KEYWORDS, SiteProfile, profile_prompt_context
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
            site_context=profile_prompt_context(self.profile),
        )

    def get_known_escalation_keywords(self) -> list[str]:
        return self.profile.escalation_keywords or list(DEFAULT_ESCALATION_KEYWORDS)
