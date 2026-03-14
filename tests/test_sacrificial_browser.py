from pathlib import Path

from ava.automation.sacrificial_browser import (
    choose_isolated_browser,
    next_tab_index,
    normalize_browser_url,
    requires_browser_confirmation,
)


def test_normalize_browser_url_adds_https_for_domains() -> None:
    assert normalize_browser_url("example.com") == "https://example.com"
    assert normalize_browser_url("https://example.com") == "https://example.com"


def test_requires_confirmation_for_sensitive_urls_and_tab_close() -> None:
    assert requires_browser_confirmation(action_name="close_current_tab") is True
    assert (
        requires_browser_confirmation(
            action_name="open_url",
            url="https://www.instagram.com/accounts/login/",
        )
        is True
    )
    assert (
        requires_browser_confirmation(
            action_name="open_url",
            url="https://web.whatsapp.com",
        )
        is True
    )
    assert (
        requires_browser_confirmation(
            action_name="open_url",
            url="https://www.youtube.com",
        )
        is False
    )


def test_next_tab_index_wraps() -> None:
    assert next_tab_index(0, 3, "next") == 1
    assert next_tab_index(2, 3, "next") == 0
    assert next_tab_index(0, 3, "previous") == 2


def test_choose_isolated_browser_prefers_available_choice(monkeypatch) -> None:
    available = {
        "edge": FileNotFoundError("missing"),
        "chrome": Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    }

    def fake_browser_executable(browser_name: str) -> Path:
        result = available[browser_name]
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(
        "ava.automation.sacrificial_browser.browser_executable",
        fake_browser_executable,
    )

    assert choose_isolated_browser("edge") == "chrome"
