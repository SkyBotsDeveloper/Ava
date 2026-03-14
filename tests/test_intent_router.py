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


def test_address_bar_focus_intent_detected() -> None:
    router = IntentRouter()

    intent = router.parse("Address bar par jao")

    assert intent.intent_type is IntentType.FOCUS_ADDRESS_BAR


def test_new_tab_intent_detected() -> None:
    router = IntentRouter()

    intent = router.parse("New tab kholo")

    assert intent.intent_type is IntentType.OPEN_NEW_TAB


def test_page_search_intent_detected() -> None:
    router = IntentRouter()

    intent = router.parse('Is page par "Wikipedia" search karo')

    assert intent.intent_type is IntentType.SEARCH_PAGE
    assert intent.metadata["query"] == "Wikipedia"


def test_page_info_intent_detected() -> None:
    router = IntentRouter()

    intent = router.parse("Current page ka title url batao")

    assert intent.intent_type is IntentType.GET_CURRENT_PAGE


def test_youtube_playlist_intent_detected() -> None:
    router = IntentRouter()

    intent = router.parse("YouTube par lofi hip hop playlist chalao")

    assert intent.intent_type is IntentType.PLAY_YOUTUBE_PLAYLIST
    assert intent.metadata["query"] == "lofi hip hop"


def test_instagram_login_intent_detected() -> None:
    router = IntentRouter()

    intent = router.parse("Instagram login page kholo")

    assert intent.intent_type is IntentType.OPEN_INSTAGRAM_LOGIN


def test_whatsapp_web_intent_detected() -> None:
    router = IntentRouter()

    intent = router.parse("WhatsApp Web kholo")

    assert intent.intent_type is IntentType.OPEN_WHATSAPP_WEB


def test_file_url_open_intent_detected() -> None:
    router = IntentRouter()

    intent = router.parse("Open file:///C:/temp/ava-tab-test.html")

    assert intent.intent_type is IntentType.OPEN_WEBSITE
    assert intent.metadata["url"] == "file:///C:/temp/ava-tab-test.html"


def test_bare_domain_open_intent_detected() -> None:
    router = IntentRouter()

    intent = router.parse("python.org kholo")

    assert intent.intent_type is IntentType.OPEN_WEBSITE
    assert intent.metadata["url"] == "https://python.org"


def test_split_voice_website_phrase_normalizes_to_browser_open() -> None:
    router = IntentRouter()

    intent = router.parse("We b site Holo.", source="voice")

    assert intent.intent_type is IntentType.OPEN_BROWSER


def test_split_voice_address_bar_phrase_normalizes_to_focus() -> None:
    router = IntentRouter()

    intent = router.parse("ad dre ss ball par jo", source="voice")

    assert intent.intent_type is IntentType.FOCUS_ADDRESS_BAR


def test_split_voice_confirmation_phrase_normalizes() -> None:
    router = IntentRouter()

    intent = router.parse("Yes.", source="voice")

    assert intent.intent_type is IntentType.CONFIRM


def test_split_voice_instagram_login_phrase_normalizes() -> None:
    router = IntentRouter()

    intent = router.parse("O pen In sta gram lo gin page.", source="voice")

    assert intent.intent_type is IntentType.OPEN_INSTAGRAM_LOGIN


def test_split_voice_whatsapp_phrase_normalizes() -> None:
    router = IntentRouter()

    intent = router.parse("O pen Wha tsApp web.", source="voice")

    assert intent.intent_type is IntentType.OPEN_WHATSAPP_WEB


def test_split_voice_python_domain_phrase_normalizes() -> None:
    router = IntentRouter()

    intent = router.parse("Pyt hon. org", source="voice")

    assert intent.intent_type is IntentType.OPEN_WEBSITE
    assert intent.metadata["url"] == "https://python.org"


def test_split_voice_search_phrase_normalizes() -> None:
    router = IntentRouter()

    intent = router.parse("sear ch Pyt hon on page.", source="voice")

    assert intent.intent_type is IntentType.SEARCH_PAGE
    assert intent.metadata["query"] == "python"


def test_split_voice_tab_switch_phrase_normalizes() -> None:
    router = IntentRouter()

    intent = router.parse("Ta p Switch.", source="voice")

    assert intent.intent_type is IntentType.SWITCH_TAB


def test_known_folder_open_detected() -> None:
    router = IntentRouter()

    intent = router.parse("Desktop kholo")

    assert intent.intent_type is IntentType.OPEN_FOLDER
    assert intent.metadata["target_name"] == "desktop"


def test_reverse_page_search_intent_detected() -> None:
    router = IntentRouter()

    intent = router.parse("Is page par Python search karo")

    assert intent.intent_type is IntentType.SEARCH_PAGE
    assert intent.metadata["query"] == "Python"


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
