"""American Express site adapter."""

from src.sites.base import BaseSiteAdapter
from src.sites.prompt_renderer import render_site_prompt


class AmexAdapter(BaseSiteAdapter):
    @classmethod
    def hostname_patterns(cls) -> list[str]:
        return ["americanexpress.com"]

    @property
    def name(self) -> str:
        return "American Express"

    @property
    def chat_url(self) -> str:
        return "https://www.americanexpress.com/us/customer-service/"

    @property
    def login_url(self) -> str:
        """URL for the Amex login page."""
        return "https://www.americanexpress.com/en-us/account/login"

    @property
    def requires_login(self) -> bool:
        return True

    def build_task_prompt(
        self,
        user_task: str,
        escalation_instructions: str,
        detection_instructions: str,
        template_id: str | None = None,
    ) -> str:
        return render_site_prompt(
            site="amex",
            base_prompt_file="base.txt",
            user_task=user_task,
            escalation_instructions=escalation_instructions,
            detection_instructions=detection_instructions,
            template_id=template_id,
        )

    def get_known_escalation_keywords(self) -> list[str]:
        return [
            "supervisor",
            "manager",
            "retention",
            "cancel my card",
            "close my account",
            "formal complaint",
            "human representative",
            "loyalty department",
        ]
