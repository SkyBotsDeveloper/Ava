from ava.automation.browser import BrowserController
from ava.config.settings import Settings


def test_browser_controller_prefers_live_session() -> None:
    settings = Settings(_env_file=None, preferred_browser="edge")
    controller = BrowserController(settings)

    browser = controller.detect_live_session(["chrome.exe", "msedge.exe"])

    assert browser == "edge"


def test_browser_controller_falls_back_to_preferred_browser() -> None:
    settings = Settings(_env_file=None, preferred_browser="edge")
    controller = BrowserController(settings)

    plan = controller.resolve_browser_plan([])

    assert plan.uses_live_session is False
    assert plan.browser_name == "edge"
