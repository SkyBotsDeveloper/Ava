from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from typing import ClassVar
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

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

logger = logging.getLogger(__name__)


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

        available = {
            browser_name
            for process_name, browser_name in self.PROCESS_TO_BROWSER.items()
            if process_name in process_names
        }
        preferred = self.settings.preferred_browser
        if preferred in available:
            return preferred
        if preferred == "edge":
            return None
        for browser in ("edge", "chrome"):
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
                return self._live_page_state(plan.browser_name, fallback_url=url)
        start_url_in_browser(plan.browser_name, url)
        return self._live_page_state(plan.browser_name, fallback_url=url, launch_wait_seconds=1.8)

    def focus_address_bar(self) -> BrowserPageState:
        plan = self.resolve_browser_plan()
        if plan.uses_isolated_session:
            return self.sacrificial_controller.focus_address_bar()
        if not self.window_controller.focus_address_bar_in_browser(
            browser_process_names(plan.browser_name)
        ):
            raise RuntimeError("Browser address bar focus nahi ho saka.")
        return self._live_page_state(plan.browser_name)

    def navigate_to_url(self, url: str, *, confirmed: bool = False) -> BrowserPageState:
        return self.open_url(url, confirmed=confirmed)

    def open_new_tab(self, url: str = "about:blank") -> BrowserPageState:
        plan = self.resolve_browser_plan()
        if plan.uses_isolated_session:
            return self.sacrificial_controller.open_new_tab(url)
        if not self.window_controller.open_new_tab_in_browser(
            browser_process_names(plan.browser_name),
            url,
        ):
            raise RuntimeError("Browser me naya tab nahi khul saka.")
        return self._live_page_state(plan.browser_name, fallback_url=url)

    def close_current_tab(self, *, confirmed: bool = False) -> BrowserPageState:
        plan = self.resolve_browser_plan()
        if plan.uses_isolated_session:
            return self.sacrificial_controller.close_current_tab(confirmed=confirmed)
        process_names = browser_process_names(plan.browser_name)
        if not self.window_controller.close_active_tab(process_names):
            raise RuntimeError("No live browser window available for tab control.")
        return self._live_page_state(plan.browser_name)

    def switch_tab(self, *, direction: str = "next") -> BrowserPageState:
        plan = self.resolve_browser_plan()
        if plan.uses_isolated_session:
            return self.sacrificial_controller.switch_tab(direction=direction)
        if not self.window_controller.switch_browser_tab(
            browser_process_names(plan.browser_name),
            direction=direction,
        ):
            raise RuntimeError("Browser tab switch nahi ho saka.")
        return self._live_page_state(plan.browser_name)

    def search_on_page(self, query: str) -> PageSearchResult:
        plan = self.resolve_browser_plan()
        if plan.uses_isolated_session:
            return self.sacrificial_controller.search_on_page(query)
        if not self.window_controller.search_on_page_in_browser(
            browser_process_names(plan.browser_name),
            query,
        ):
            raise RuntimeError("Browser page search start nahi ho saka.")
        return PageSearchResult(
            query=query,
            match_count=-1,
            page=self._live_page_state(plan.browser_name),
        )

    def current_page_state(self) -> BrowserPageState:
        plan = self.resolve_browser_plan()
        if plan.uses_isolated_session:
            return self.sacrificial_controller.current_page_state()
        return self._live_page_state(plan.browser_name)

    def open_youtube(self) -> BrowserPageState:
        return self.open_url("https://www.youtube.com")

    def search_youtube(
        self,
        search_query: str,
        *,
        open_first: bool = False,
    ) -> tuple[BrowserPageState, dict[str, str | bool]]:
        if open_first:
            open_page = self.open_youtube()
            logger.info(
                "Executed YouTube open step before search",
                extra={
                    "event": "youtube_open_step_executed",
                    "query": search_query,
                    "page_title": open_page.title,
                    "page_url": open_page.url,
                    "browser_name": open_page.browser_name,
                    "isolated": open_page.isolated,
                },
            )

        target_url = f"https://www.youtube.com/results?search_query={quote_plus(search_query)}"
        page = self.open_url(target_url)
        verification = self._verify_youtube_search_result(
            page=page,
            query=search_query,
            target_url=target_url,
        )
        logger.info(
            "Submitted YouTube search in browser",
            extra={
                "event": "youtube_search_submitted",
                "query": search_query,
                "final_title": page.title,
                "final_url": page.url,
                "browser_name": page.browser_name,
                "isolated": page.isolated,
                **verification,
            },
        )
        logger.info(
            "Observed final browser state after search submission",
            extra={
                "event": "browser_final_state_observed",
                "query": search_query,
                "final_title": page.title,
                "final_url": page.url,
                "browser_name": page.browser_name,
                "isolated": page.isolated,
                **verification,
            },
        )
        return page, verification

    def play_youtube_playlist(self, search_query: str) -> PlaybackResult:
        plan = self.resolve_browser_plan()
        if plan.uses_isolated_session:
            playback = self.sacrificial_controller.search_and_play_youtube_playlist(search_query)
            logger.info(
                "Attempted YouTube playlist open in isolated browser",
                extra={
                    "event": "youtube_playlist_result_open_attempted",
                    "query": search_query,
                    "selected_href": playback.selected_href or "",
                    "final_title": playback.page.title,
                    "final_url": playback.page.url,
                    "browser_name": playback.page.browser_name,
                    "isolated": playback.page.isolated,
                },
            )
            return playback
        target_url = self._resolve_youtube_target_url(search_query) or (
            f"https://www.youtube.com/results?search_query={quote_plus(search_query + ' playlist')}"
        )
        logger.info(
            "Attempting YouTube playlist result open",
            extra={
                "event": "youtube_playlist_result_open_attempted",
                "query": search_query,
                "target_url": target_url,
                "browser_name": plan.browser_name,
                "isolated": False,
            },
        )
        page = self.open_url(target_url)
        playback = PlaybackResult(
            search_query=search_query,
            playing=False,
            page=page,
            selected_href=target_url,
        )
        logger.info(
            "Observed final browser state after playlist open attempt",
            extra={
                "event": "browser_final_state_observed",
                "query": search_query,
                "final_title": playback.page.title,
                "final_url": playback.page.url,
                "selected_href": playback.selected_href or "",
                "browser_name": playback.page.browser_name,
                "isolated": playback.page.isolated,
            },
        )
        return playback

    def open_instagram_login(self, *, confirmed: bool = False) -> BrowserPageState:
        plan = self.resolve_browser_plan()
        if plan.uses_isolated_session:
            return self.sacrificial_controller.open_instagram_login(confirmed=confirmed)
        return self.open_url("https://www.instagram.com/accounts/login/", confirmed=confirmed)

    def open_whatsapp_web(self, *, confirmed: bool = False) -> BrowserPageState:
        plan = self.resolve_browser_plan()
        if plan.uses_isolated_session:
            return self.sacrificial_controller.open_whatsapp_web(confirmed=confirmed)
        return self.open_url("https://web.whatsapp.com", confirmed=confirmed)

    def executable_for(self, browser_name: str) -> str:
        return str(browser_executable(browser_name))

    def _live_page_state(
        self,
        browser_name: str,
        *,
        fallback_url: str = "",
        launch_wait_seconds: float = 0.6,
    ) -> BrowserPageState:
        if launch_wait_seconds > 0:
            import time

            time.sleep(launch_wait_seconds)
        page_info = self.window_controller.current_browser_title_and_url(
            browser_process_names(browser_name)
        )
        if page_info is None:
            return BrowserPageState(
                title="",
                url=fallback_url,
                tab_count=1 if fallback_url else 0,
                active_tab_index=0,
                browser_name=browser_name,
                isolated=False,
            )
        title, url = page_info
        return BrowserPageState(
            title=title,
            url=url or fallback_url,
            tab_count=1,
            active_tab_index=0,
            browser_name=browser_name,
            isolated=False,
        )

    def _resolve_youtube_target_url(self, search_query: str) -> str | None:
        search_url = (
            f"https://www.youtube.com/results?search_query={quote_plus(search_query + ' playlist')}"
        )
        request = Request(
            search_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                )
            },
        )
        with urlopen(request, timeout=10) as response:
            html = response.read().decode("utf-8", errors="ignore")
        video_ids = re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', html)
        if video_ids:
            return f"https://www.youtube.com/watch?v={video_ids[0]}"
        playlist_ids = re.findall(r'"playlistId":"([A-Za-z0-9_-]+)"', html)
        if playlist_ids:
            return f"https://www.youtube.com/playlist?list={playlist_ids[0]}"
        return None

    @staticmethod
    def _verify_youtube_search_result(
        *,
        page: BrowserPageState,
        query: str,
        target_url: str,
    ) -> dict[str, str | bool]:
        final_url = page.url.lower()
        final_title = page.title.lower()
        expected_query = quote_plus(query).lower()
        results_url_observed = "youtube.com/results" in final_url and expected_query in final_url
        query_box_value_observed = False
        visible_results_state_observed = "youtube" in final_title and (
            "results" in final_title or results_url_observed
        )
        expected_page_transition_confirmed = results_url_observed or final_url.rstrip(
            "/"
        ) == target_url.lower().rstrip("/")
        verified_via = [
            name
            for name, enabled in (
                ("results_url_observed", results_url_observed),
                ("query_box_value_observed", query_box_value_observed),
                ("visible_results_state_observed", visible_results_state_observed),
                ("expected_page_transition_confirmed", expected_page_transition_confirmed),
            )
            if enabled
        ]
        return {
            "results_url_observed": results_url_observed,
            "query_box_value_observed": query_box_value_observed,
            "visible_results_state_observed": visible_results_state_observed,
            "expected_page_transition_confirmed": expected_page_transition_confirmed,
            "action_verified": bool(verified_via),
            "verified_via": ",".join(verified_via),
        }
