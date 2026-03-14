from ava.intents.models import IntentType
from ava.intents.router import IntentRouter


def test_cancel_intent_is_immediate() -> None:
    router = IntentRouter()

    intent = router.parse("Stop Ava")

    assert intent.intent_type is IntentType.CANCEL
    assert intent.immediate is True


def test_browser_intent_detected_for_hinglish_command() -> None:
    router = IntentRouter()

    intent = router.parse("Ava, insta kholo")

    assert intent.intent_type is IntentType.OPEN_WEBSITE
    assert intent.metadata["url"] == "https://www.instagram.com"


def test_notepad_open_intent_detected() -> None:
    router = IntentRouter()

    intent = router.parse("Ava, notepad kholo")

    assert intent.intent_type is IntentType.OPEN_APP
    assert intent.metadata["app_name"] == "notepad"


def test_close_tab_intent_detected() -> None:
    router = IntentRouter()

    intent = router.parse("Ye tab band karo")

    assert intent.intent_type is IntentType.CLOSE_TAB


def test_file_url_open_intent_detected() -> None:
    router = IntentRouter()

    intent = router.parse("Open file:///C:/temp/ava-tab-test.html")

    assert intent.intent_type is IntentType.OPEN_WEBSITE
    assert intent.metadata["url"] == "file:///C:/temp/ava-tab-test.html"
