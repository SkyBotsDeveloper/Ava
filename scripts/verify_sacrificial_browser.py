from __future__ import annotations

import json

from ava.automation.sacrificial_browser import (
    SacrificialBrowserController,
    requires_browser_confirmation,
)
from ava.config.settings import load_settings


def main() -> None:
    settings = load_settings()
    results: dict[str, object] = {}

    with SacrificialBrowserController(settings) as browser:
        session = browser.session_info
        results["session"] = {
            "browser_name": session.browser_name,
            "user_data_dir": str(session.user_data_dir),
            "remote_debugging_port": session.remote_debugging_port,
            "strategy": session.strategy.value,
        }

        results["open_website"] = browser.open_website("https://example.com").as_dict()
        results["focus_address_bar"] = browser.focus_address_bar().as_dict()
        results["navigate_url"] = browser.navigate_to_url("https://www.python.org").as_dict()
        results["open_new_tab"] = browser.open_new_tab("https://www.wikipedia.org").as_dict()
        results["switch_previous_tab"] = browser.switch_tab(direction="previous").as_dict()
        results["switch_next_tab"] = browser.switch_tab(direction="next").as_dict()
        results["page_search"] = browser.search_on_page("Wikipedia").as_dict()
        results["page_info"] = browser.current_page_state().as_dict()
        results["close_tab_confirmation_required"] = requires_browser_confirmation(
            action_name="close_current_tab"
        )
        try:
            browser.close_current_tab()
        except PermissionError as exc:
            results["close_tab_blocked_without_confirmation"] = str(exc)
        results["close_current_tab"] = browser.close_current_tab(confirmed=True).as_dict()
        results["youtube_playlist"] = browser.search_and_play_youtube_playlist(
            "lofi hip hop"
        ).as_dict()
        try:
            browser.open_instagram_login()
        except PermissionError as exc:
            results["instagram_blocked_without_confirmation"] = str(exc)
        results["instagram_login"] = browser.open_instagram_login(confirmed=True).as_dict()
        try:
            browser.open_whatsapp_web()
        except PermissionError as exc:
            results["whatsapp_blocked_without_confirmation"] = str(exc)
        results["whatsapp_web"] = browser.open_whatsapp_web(confirmed=True).as_dict()

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
