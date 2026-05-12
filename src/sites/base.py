"""Abstract base class for site-specific adapters.

Every runnable site path is exposed as an adapter. Most websites use the
shared profile-backed adapter; bespoke adapters are reserved for sites with
unusual mechanics or recovery policies.
"""

from abc import ABC, abstractmethod


class BaseSiteAdapter(ABC):
    """Base class for all site adapters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable site name."""
        ...

    @property
    @abstractmethod
    def chat_url(self) -> str:
        """URL to navigate to for initiating chat."""
        ...

    @property
    @abstractmethod
    def requires_login(self) -> bool:
        """Whether the site requires authentication before chatting."""
        ...

    @abstractmethod
    def build_task_prompt(
        self,
        user_task: str,
        escalation_instructions: str,
        detection_instructions: str,
        template_id: str | None = None,
    ) -> str:
        """Build the full task prompt for the browser-use agent.

        Combines the user's task with site-specific context, detection
        instructions, and escalation strategies.
        """
        ...

    def get_known_escalation_keywords(self) -> list[str]:
        """Site-specific keywords known to trigger human escalation."""
        return ["supervisor", "manager", "complaint", "escalate", "human agent"]

    @classmethod
    def hostname_patterns(cls) -> list[str]:
        """Substrings matched against the tab URL to auto-resolve this adapter.

        Return an empty list for adapters that should never match (e.g. the
        generic fallback). Matching is case-insensitive substring on the
        full URL (host + path), so 'americanexpress.com' works.
        """
        return []
