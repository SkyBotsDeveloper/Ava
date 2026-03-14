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


def test_known_folder_open_detected() -> None:
    router = IntentRouter()

    intent = router.parse("Desktop kholo")

    assert intent.intent_type is IntentType.OPEN_FOLDER
    assert intent.metadata["target_name"] == "desktop"


def test_move_path_detected() -> None:
    router = IntentRouter()

    intent = router.parse('"alpha" ko "beta" move karo')

    assert intent.intent_type is IntentType.MOVE_PATH
    assert intent.metadata["source_name"] == "alpha"
    assert intent.metadata["destination_name"] == "beta"


def test_move_path_detected_when_move_starts_command() -> None:
    router = IntentRouter()

    intent = router.parse('Move "alpha" to "beta"')

    assert intent.intent_type is IntentType.MOVE_PATH
    assert intent.metadata["source_name"] == "alpha"
    assert intent.metadata["destination_name"] == "beta"


def test_rename_path_detected() -> None:
    router = IntentRouter()

    intent = router.parse('Rename "alpha" to "beta"')

    assert intent.intent_type is IntentType.RENAME_PATH
    assert intent.metadata["source_name"] == "alpha"
    assert intent.metadata["new_name"] == "beta"


def test_open_folder_prefers_quoted_absolute_path_over_known_alias() -> None:
    router = IntentRouter()
    sample_path = (
        "C:\\Users\\strad\\OneDrive\\Documents\\shortcuts\\Downloads\\Ava\\.artifacts\\sample"
    )

    intent = router.parse(f'Open "{sample_path}" folder')

    assert intent.intent_type is IntentType.OPEN_FOLDER
    assert intent.metadata["target_name"].endswith("\\sample")
