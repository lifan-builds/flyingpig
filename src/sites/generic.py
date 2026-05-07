"""Generic site adapter for unknown customer-service chat widgets."""

from src.sites.base import BaseSiteAdapter
from src.sites.prompt_renderer import render_site_prompt


class GenericAdapter(BaseSiteAdapter):
    @property
    def name(self) -> str:
        return "Generic (auto-detect chat)"

    @property
    def chat_url(self) -> str:
        # Unused when attached via CDP: the user has already navigated.
        return ""

    @property
    def requires_login(self) -> bool:
        # We never drive login for unknown sites; user is already signed in.
        return False

    @classmethod
    def hostname_patterns(cls) -> list[str]:
        # Never auto-matches by URL; registry returns this only as a fallback.
        return []

    def build_task_prompt(
        self,
        user_task: str,
        escalation_instructions: str,
        detection_instructions: str,
        template_id: str | None = None,
    ) -> str:
        return render_site_prompt(
            site="generic",
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
            "cancel my account",
            "close my account",
            "formal complaint",
            "human representative",
            "real person",
            "agent please",
        ]
