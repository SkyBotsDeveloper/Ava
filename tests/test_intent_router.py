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

    assert intent.intent_type is IntentType.OPEN_BROWSER
