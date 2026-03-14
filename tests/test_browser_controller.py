from ava.automation.browser import BrowserController
from ava.config.settings import Settings


def test_browser_controller_prefers_live_edge_plan_by_default() -> None:
    settings = Settings(_env_file=None, preferred_browser="edge")
    controller = BrowserController(settings)

    plan = controller.resolve_browser_plan(["chrome.exe", "msedge.exe"])

    assert plan.uses_isolated_session is False
    assert plan.uses_live_session is True
    assert plan.browser_name == "edge"


def test_browser_controller_prefers_live_session_when_live_mode_enabled() -> None:
    settings = Settings(_env_file=None, preferred_browser="edge", browser_command_mode="live")
    controller = BrowserController(settings)

    browser = controller.detect_live_session(["chrome.exe", "msedge.exe"])

    assert browser == "edge"


def test_browser_controller_falls_back_to_preferred_browser_in_live_mode() -> None:
    settings = Settings(_env_file=None, preferred_browser="edge", browser_command_mode="live")
    controller = BrowserController(settings)

    plan = controller.resolve_browser_plan(["chrome.exe"])

    assert plan.uses_isolated_session is False
    assert plan.uses_live_session is False
    assert plan.browser_name == "edge"
