"""American Express site adapter."""

from src.sites.base import BaseSiteAdapter
from src.sites.profiles import AMEX_PROFILE
from src.sites.prompt_renderer import render_site_prompt


class AmexAdapter(BaseSiteAdapter):
    @classmethod
    def hostname_patterns(cls) -> list[str]:
        return list(AMEX_PROFILE.hostname_patterns)

    @property
    def name(self) -> str:
        return AMEX_PROFILE.name

    @property
    def chat_url(self) -> str:
        return AMEX_PROFILE.chat_url

    @property
    def login_url(self) -> str:
        """URL for the Amex login page."""
        return AMEX_PROFILE.login_url or "https://www.americanexpress.com/en-us/account/login"

    @property
    def requires_login(self) -> bool:
        return AMEX_PROFILE.requires_login

    def build_task_prompt(
        self,
        user_task: str,
        escalation_instructions: str,
        detection_instructions: str,
        template_id: str | None = None,
    ) -> str:
        return render_site_prompt(
            site=AMEX_PROFILE.template_site,
            base_prompt_file="base.txt",
            user_task=user_task,
            escalation_instructions=escalation_instructions,
            detection_instructions=detection_instructions,
            template_id=template_id,
        )

    def get_known_escalation_keywords(self) -> list[str]:
        return [
            *AMEX_PROFILE.escalation_keywords,
        ]
