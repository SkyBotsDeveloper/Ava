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


def test_youtube_search_intent_detected() -> None:
    router = IntentRouter()

    intent = router.parse("YouTube par lofi hip hop playlist search karo")

    assert intent.intent_type is IntentType.SEARCH_YOUTUBE
    assert intent.metadata["query"] == "lofi hip hop playlist"
    assert intent.metadata["compound_open_first"] == "true"


def test_compound_youtube_open_and_search_intent_detected() -> None:
    router = IntentRouter()

    intent = router.parse("YouTube kholo aur lofi hip hop playlist search karo")

    assert intent.intent_type is IntentType.SEARCH_YOUTUBE
    assert intent.metadata["query"] == "lofi hip hop playlist"
    assert intent.metadata["compound_open_first"] == "true"


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


def test_split_voice_han_confirmation_phrase_normalizes() -> None:
    router = IntentRouter()

    intent = router.parse("Han.", source="voice")

    assert intent.intent_type is IntentType.CONFIRM


def test_split_voice_han_confirmation_with_noise_normalizes() -> None:
    router = IntentRouter()

    intent = router.parse("Han. <noise>", source="voice")

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


def test_specific_folder_open_detected_without_folder_keyword() -> None:
    router = IntentRouter()

    intent = router.parse("Ava-Test kholo")

    assert intent.intent_type is IntentType.OPEN_FOLDER
    assert intent.metadata["target_name"] == "Ava-Test"


def test_fragmented_known_folder_open_detected() -> None:
    router = IntentRouter()

    intent = router.parse("des ktop kholo")

    assert intent.intent_type is IntentType.OPEN_FOLDER
    assert intent.metadata["target_name"] == "desktop"


def test_contextual_file_create_detected() -> None:
    router = IntentRouter()

    intent = router.parse("Is folder me new file banao")

    assert intent.intent_type is IntentType.CREATE_FILE
    assert intent.metadata["use_active_folder_context"] == "true"


def test_contextual_folder_create_detected() -> None:
    router = IntentRouter()

    intent = router.parse("Is folder me new folder banao")

    assert intent.intent_type is IntentType.CREATE_FOLDER
    assert intent.metadata["use_active_folder_context"] == "true"


def test_contextual_file_rename_detected() -> None:
    router = IntentRouter()

    intent = router.parse("Is file ka naam badlo ava renamed note")

    assert intent.intent_type is IntentType.RENAME_PATH
    assert intent.metadata["use_active_file_context"] == "true"
    assert intent.metadata["new_name"] == "ava renamed note"


def test_contextual_file_rename_detected_without_naam_phrase() -> None:
    router = IntentRouter()

    intent = router.parse("Is file bad low phase 4 note", source="voice")

    assert intent.intent_type is IntentType.RENAME_PATH
    assert intent.metadata["use_active_file_context"] == "true"
    assert intent.metadata["new_name"] == "phase 4 note"


def test_contextual_folder_move_detected() -> None:
    router = IntentRouter()

    intent = router.parse("Is folder ko downloads me move karo")

    assert intent.intent_type is IntentType.MOVE_PATH
    assert intent.metadata["use_active_folder_context"] == "true"
    assert intent.metadata["destination_name"] == "downloads"


def test_contextual_folder_move_detected_with_fragmented_archive_phrase() -> None:
    router = IntentRouter()

    intent = router.parse("Is fo lder KO ar chi ve me move.", source="voice")

    assert intent.intent_type is IntentType.MOVE_PATH
    assert intent.metadata["use_active_folder_context"] == "true"
    assert intent.metadata["destination_name"] == "archive"


def test_window_minimize_intent_detected() -> None:
    router = IntentRouter()

    intent = router.parse("Is window ko minimize karo")

    assert intent.intent_type is IntentType.MINIMIZE_WINDOW


def test_window_maximize_intent_detected() -> None:
    router = IntentRouter()

    intent = router.parse("Is window ko maximize karo")

    assert intent.intent_type is IntentType.MAXIMIZE_WINDOW


def test_next_window_intent_detected() -> None:
    router = IntentRouter()

    intent = router.parse("Next window par jao")

    assert intent.intent_type is IntentType.NEXT_WINDOW


def test_focus_current_app_intent_detected() -> None:
    router = IntentRouter()

    intent = router.parse("Is app par focus karo")

    assert intent.intent_type is IntentType.FOCUS_APP
    assert intent.metadata["use_active_app_context"] == "true"


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
