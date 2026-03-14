from __future__ import annotations

from collections.abc import Iterable
from typing import ClassVar

import psutil

from ava.automation.models import AutomationStrategy, BrowserPlan
from ava.automation.sacrificial_browser import (
    BrowserPageState,
    PageSearchResult,
    PlaybackResult,
    SacrificialBrowserController,
    choose_isolated_browser,
)
from ava.automation.windows import (
    WindowController,
    browser_executable,
    browser_process_names,
    start_url_in_browser,
)
from ava.config.settings import Settings


class BrowserController:
    PROCESS_TO_BROWSER: ClassVar[dict[str, str]] = {
        "msedge.exe": "edge",
        "chrome.exe": "chrome",
    }

    def __init__(
        self,
        settings: Settings,
        window_controller: WindowController | None = None,
        sacrificial_controller: SacrificialBrowserController | None = None,
    ) -> None:
        self.settings = settings
        self.window_controller = window_controller or WindowController()
        self.sacrificial_controller = sacrificial_controller or SacrificialBrowserController(
            settings
        )

    @property
    def command_mode(self) -> str:
        return self.settings.browser_command_mode

    def detect_live_session(self, running_processes: Iterable[str] | None = None) -> str | None:
        process_names = {
            name.lower()
            for name in (
                running_processes
                if running_processes is not None
                else ((proc.info.get("name") or "") for proc in psutil.process_iter(["name"]))
            )
            if name
        }

        preferred_order = [self.settings.preferred_browser, "chrome", "edge"]
        seen: list[str] = []
        for browser in preferred_order:
            if browser not in seen:
                seen.append(browser)

        available = {
            browser_name
            for process_name, browser_name in self.PROCESS_TO_BROWSER.items()
            if process_name in process_names
        }
        for browser in seen:
            if browser in available:
                return browser
        return None

    def resolve_browser_plan(self, running_processes: Iterable[str] | None = None) -> BrowserPlan:
        if self.command_mode == "isolated":
            browser_name = choose_isolated_browser(self.settings.preferred_browser)
            return BrowserPlan(
                uses_live_session=False,
                uses_isolated_session=True,
                browser_name=browser_name,
                strategy=AutomationStrategy.DOM_AUTOMATION,
                reason="Use the isolated sacrificial browser session.",
            )

        if self.settings.browser_live_session_first:
            live_browser = self.detect_live_session(running_processes)
            if live_browser:
                return BrowserPlan(
                    uses_live_session=True,
                    uses_isolated_session=False,
                    browser_name=live_browser,
                    strategy=AutomationStrategy.UI_AUTOMATION,
                    reason="Detected a running browser session.",
                )

        fallback_browser = self.settings.preferred_browser
        return BrowserPlan(
            uses_live_session=False,
            uses_isolated_session=False,
            browser_name=fallback_browser,
            strategy=AutomationStrategy.UI_AUTOMATION,
            reason="No suitable live session found; launch the preferred browser profile.",
        )

    def open_url(self, url: str, *, confirmed: bool = False) -> BrowserPageState:
        plan = self.resolve_browser_plan()
        if plan.uses_isolated_session:
            return self.sacrificial_controller.open_website(url, confirmed=confirmed)
        process_names = browser_process_names(plan.browser_name)
        if plan.uses_live_session:
            opened = self.window_controller.open_url_in_active_browser(process_names, url)
            if opened:
                return BrowserPageState(
                    title="",
                    url=url,
                    tab_count=0,
                    active_tab_index=0,
                    browser_name=plan.browser_name,
                    isolated=False,
                )
        start_url_in_browser(plan.browser_name, url)
        return BrowserPageState(
            title="",
            url=url,
            tab_count=1,
            active_tab_index=0,
            browser_name=plan.browser_name,
            isolated=False,
        )

    def focus_address_bar(self) -> BrowserPageState:
        plan = self.resolve_browser_plan()
        if not plan.uses_isolated_session:
            raise RuntimeError("Address bar focus abhi isolated browser mode me hi supported hai.")
        return self.sacrificial_controller.focus_address_bar()

    def navigate_to_url(self, url: str, *, confirmed: bool = False) -> BrowserPageState:
        plan = self.resolve_browser_plan()
        if plan.uses_isolated_session:
            return self.sacrificial_controller.navigate_to_url(url, confirmed=confirmed)
        return self.open_url(url, confirmed=confirmed)

    def open_new_tab(self, url: str = "about:blank") -> BrowserPageState:
        plan = self.resolve_browser_plan()
        if not plan.uses_isolated_session:
            raise RuntimeError("New tab control abhi isolated browser mode me hi supported hai.")
        return self.sacrificial_controller.open_new_tab(url)

    def close_current_tab(self, *, confirmed: bool = False) -> BrowserPageState:
        plan = self.resolve_browser_plan()
        if plan.uses_isolated_session:
            return self.sacrificial_controller.close_current_tab(confirmed=confirmed)
        process_names = browser_process_names(plan.browser_name)
        if not self.window_controller.close_active_tab(process_names):
            raise RuntimeError("No live browser window available for tab control.")
        return BrowserPageState(
            title="",
            url="",
            tab_count=0,
            active_tab_index=0,
            browser_name=plan.browser_name,
            isolated=False,
        )

    def switch_tab(self, *, direction: str = "next") -> BrowserPageState:
        plan = self.resolve_browser_plan()
        if not plan.uses_isolated_session:
            raise RuntimeError("Tab switching abhi isolated browser mode me hi supported hai.")
        return self.sacrificial_controller.switch_tab(direction=direction)

    def search_on_page(self, query: str) -> PageSearchResult:
        plan = self.resolve_browser_plan()
        if not plan.uses_isolated_session:
            raise RuntimeError("Page search abhi isolated browser mode me hi supported hai.")
        return self.sacrificial_controller.search_on_page(query)

    def current_page_state(self) -> BrowserPageState:
        plan = self.resolve_browser_plan()
        if not plan.uses_isolated_session:
            raise RuntimeError(
                "Current page inspection abhi isolated browser mode me hi supported hai."
            )
        return self.sacrificial_controller.current_page_state()

    def open_youtube(self) -> BrowserPageState:
        plan = self.resolve_browser_plan()
        if not plan.uses_isolated_session:
            raise RuntimeError("YouTube flow abhi isolated browser mode me hi supported hai.")
        return self.sacrificial_controller.open_youtube()

    def play_youtube_playlist(self, search_query: str) -> PlaybackResult:
        plan = self.resolve_browser_plan()
        if not plan.uses_isolated_session:
            raise RuntimeError(
                "YouTube playlist flow abhi isolated browser mode me hi supported hai."
            )
        return self.sacrificial_controller.search_and_play_youtube_playlist(search_query)

    def open_instagram_login(self, *, confirmed: bool = False) -> BrowserPageState:
        plan = self.resolve_browser_plan()
        if not plan.uses_isolated_session:
            raise RuntimeError(
                "Instagram login flow abhi isolated browser mode me hi supported hai."
            )
        return self.sacrificial_controller.open_instagram_login(confirmed=confirmed)

    def open_whatsapp_web(self, *, confirmed: bool = False) -> BrowserPageState:
        plan = self.resolve_browser_plan()
        if not plan.uses_isolated_session:
            raise RuntimeError("WhatsApp Web flow abhi isolated browser mode me hi supported hai.")
        return self.sacrificial_controller.open_whatsapp_web(confirmed=confirmed)

    def executable_for(self, browser_name: str) -> str:
        return str(browser_executable(browser_name))
