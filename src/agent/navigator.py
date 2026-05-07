"""Browser navigation orchestrator.
Handles opening the target site, finding the chat widget, and managing
the browser session lifecycle. Uses browser-use + Playwright.

Supports two live browser paths:
  1. CDP attach — connect to an already-running remote-debugging browser.
  2. Controlled browser — launch a clean browser-use profile for local tests.

Production launchers should start a FlyingPig-owned CDP Chrome first, then pass
its CDP URL here. The local controlled-browser mode remains for mocks/tests.
"""

import asyncio
import logging

from browser_use.browser.events import SwitchTabEvent
from browser_use.browser.profile import BrowserProfile
from browser_use.browser.session import BrowserSession

from src.sites.base import BaseSiteAdapter

logger = logging.getLogger(__name__)


async def _bring_page_to_front(page) -> None:
    """Best-effort nudge so headful runs are visible to the user."""
    try:
        await page.bring_to_front()
    except Exception as exc:
        logger.debug(f"Playwright bring_to_front failed: {exc}")

    try:
        client = await page.context.new_cdp_session(page)
        window_info = await client.send("Browser.getWindowForTarget")
        window_id = window_info.get("windowId")
        if window_id is None:
            return
        await client.send(
            "Browser.setWindowBounds",
            {"windowId": window_id, "bounds": {"windowState": "normal"}},
        )
        await client.send(
            "Browser.setWindowBounds",
            {
                "windowId": window_id,
                "bounds": {"left": 80, "top": 80, "width": 1280, "height": 900},
            },
        )
        await client.send("Page.bringToFront")
    except Exception as exc:
        logger.debug(f"CDP window activation failed: {exc}")


class ChatNavigator:
    """Manages browser session and chat interface navigation."""

    def __init__(
        self,
        site_adapter: BaseSiteAdapter,
        headless: bool = True,
        cdp_url: str | None = None,
        browser_mode: str = "controlled",
        navigate_on_attach: bool = False,
        target_url: str | None = None,
    ):
        self.site_adapter = site_adapter
        self.headless = headless
        self.cdp_url = cdp_url
        self.browser_mode = browser_mode
        self.navigate_on_attach = navigate_on_attach
        self.target_url = target_url
        self._session: BrowserSession | None = None

    async def open_chat(self) -> BrowserSession:
        """Open a browser session for the target site.

        Modes:
          - cdp_url: attach to an already-running browser via CDP.
            The user already has the target tab open; we skip navigation.
          - browser_mode="controlled": launch a clean temporary profile for
            local mocks/tests, then navigate to the chat URL.

        Returns a BrowserSession that browser-use Agent can use.
        """
        if self.cdp_url:
            logger.info(f"Attaching to existing browser via CDP: {self.cdp_url}")
            self._session = BrowserSession(cdp_url=self.cdp_url)
        elif self.browser_mode in {"controlled", "fresh"}:
            profile = BrowserProfile(
                headless=self.headless,
                wait_for_network_idle_page_load_time=5.0,
                viewport={"width": 1920, "height": 1080},
                disable_security=False,
            )
            self._session = BrowserSession(browser_profile=profile)
        else:
            raise ValueError(
                "Unsupported browser mode. Use cdp_url for an existing tab or "
                "browser_mode='controlled' for local test runs."
            )

        await self._session.start()

        if self.cdp_url:
            if self.target_url:
                await self._focus_target_url(self.target_url)
            current_url = await self._session.get_current_page_url()
            logger.info(f"Attached to user's active tab: {current_url}")
            if self.navigate_on_attach:
                logger.info(
                    "Navigating attached tab to %s", self.site_adapter.chat_url
                )
                page = await self._session.get_current_page()
                await page.goto(self.site_adapter.chat_url)
                await _bring_page_to_front(page)
                await asyncio.sleep(2)
        else:
            logger.info(f"Navigating to {self.site_adapter.chat_url}")
            page = await self._session.get_current_page()
            await page.goto(self.site_adapter.chat_url)
            await _bring_page_to_front(page)
            await asyncio.sleep(2)

        return self._session

    async def _focus_target_url(self, target_url: str) -> None:
        """Focus the user tab selected by the side panel before browser-use acts."""
        if self._session is None:
            raise RuntimeError("Browser session not started.")

        try:
            target_id = await self._session.get_target_id_from_url(target_url)
            await self._session.on_SwitchTabEvent(SwitchTabEvent(target_id=target_id))
            page = await self._session.get_current_page()
            if page:
                await _bring_page_to_front(page)
            logger.info("Focused attached browser tab for target URL: %s", target_url)
        except Exception as exc:
            logger.warning(
                "Could not focus requested target URL %s before attach: %s",
                target_url,
                exc,
            )

    async def wait_for_login(self, input_handler=None) -> None:
        """Pause execution and wait for user to log in manually.

        This is the safest approach — no credential storage, no PII risk.
        The user sees the browser window and logs in themselves.

        Skipped when using CDP attach: the user's existing browser
        already holds the authenticated session.
        """
        if not self.site_adapter.requires_login:
            return
        if self.cdp_url or self.browser_mode in {"controlled", "fresh"}:
            return

        if self._session is None:
            raise RuntimeError("Browser session not started. Call open_chat() first.")

        logger.info("Login required. Waiting for user to log in manually...")

        if input_handler:
            await input_handler.ask(
                question=(
                    "Please log in to your account in the browser window. "
                    "Press Enter here when you're done."
                ),
                reason=f"{self.site_adapter.name} requires authentication to access chat.",
            )
        else:
            logger.warning("No input handler — waiting 60 seconds for manual login...")
            await asyncio.sleep(60)

        await asyncio.sleep(3)

        page = await self._session.get_current_page()
        current_url = await page.get_url()
        logger.info(f"Post-login URL: {current_url}")

        if self.site_adapter.chat_url not in current_url:
            logger.info(f"Navigating to chat after login: {self.site_adapter.chat_url}")
            await page.goto(self.site_adapter.chat_url)
            await asyncio.sleep(2)

    async def close(self):
        """Clean up browser resources."""
        if self._session:
            if self.cdp_url:
                self._session = None
                logger.info("Detached from browser (left open).")
            elif self.browser_mode in {"controlled", "fresh"}:
                await self._session.stop()
                self._session = None
                logger.info("Browser session closed.")
