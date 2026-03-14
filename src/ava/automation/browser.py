from __future__ import annotations

from collections.abc import Iterable
from typing import ClassVar

import psutil

from ava.automation.models import AutomationStrategy, BrowserPlan
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
    ) -> None:
        self.settings = settings
        self.window_controller = window_controller or WindowController()

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
        if self.settings.browser_live_session_first:
            live_browser = self.detect_live_session(running_processes)
            if live_browser:
                return BrowserPlan(
                    uses_live_session=True,
                    browser_name=live_browser,
                    strategy=AutomationStrategy.UI_AUTOMATION,
                    reason="Detected a running browser session.",
                )

        fallback_browser = self.settings.preferred_browser
        return BrowserPlan(
            uses_live_session=False,
            browser_name=fallback_browser,
            strategy=AutomationStrategy.UI_AUTOMATION,
            reason="No suitable live session found; launch the preferred browser profile.",
        )

    def open_url(self, url: str) -> BrowserPlan:
        plan = self.resolve_browser_plan()
        process_names = browser_process_names(plan.browser_name)
        if plan.uses_live_session:
            opened = self.window_controller.open_url_in_active_browser(process_names, url)
            if opened:
                return plan
        start_url_in_browser(plan.browser_name, url)
        return BrowserPlan(
            uses_live_session=False,
            browser_name=plan.browser_name,
            strategy=AutomationStrategy.INPUT_SIMULATION,
            reason="Opened URL by launching the preferred browser executable.",
        )

    def close_current_tab(self) -> BrowserPlan:
        plan = self.resolve_browser_plan()
        process_names = browser_process_names(plan.browser_name)
        if not self.window_controller.close_active_tab(process_names):
            raise RuntimeError("No live browser window available for tab control.")
        return plan

    def executable_for(self, browser_name: str) -> str:
        return str(browser_executable(browser_name))
