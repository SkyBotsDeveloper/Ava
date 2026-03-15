from ava.intents.models import IntentType
from ava.intents.router import IntentRouter
from ava.voice.spoken_normalizer import SpokenCommandNormalizer


def test_spoken_normalizer_promotes_domain_only_phrase_to_open_command() -> None:
    normalizer = SpokenCommandNormalizer()

    interpretation = normalizer.interpret("Pyt hon.org", intent_router=IntentRouter())

    assert interpretation.normalized_text == "python.org kholo"
    assert interpretation.intent.intent_type is IntentType.OPEN_WEBSITE
    assert interpretation.intent.metadata["url"] == "https://python.org"
    assert interpretation.needs_confirmation is False


def test_spoken_normalizer_preserves_known_domain_phrase() -> None:
    normalizer = SpokenCommandNormalizer()

    interpretation = normalizer.interpret("github dot com kholo", intent_router=IntentRouter())

    assert interpretation.normalized_text == "github.com kholo"
    assert interpretation.intent.intent_type is IntentType.OPEN_WEBSITE
    assert interpretation.intent.metadata["url"] == "https://github.com"


def test_spoken_normalizer_promotes_bare_app_target_to_open_command() -> None:
    normalizer = SpokenCommandNormalizer()

    interpretation = normalizer.interpret("cal cu la tor", intent_router=IntentRouter())

    assert interpretation.normalized_text == "calculator kholo"
    assert interpretation.intent.intent_type is IntentType.OPEN_APP
    assert interpretation.intent.metadata["app_name"] == "calculator"


def test_spoken_normalizer_repairs_fragmented_documents_phrase() -> None:
    normalizer = SpokenCommandNormalizer()

    interpretation = normalizer.interpret("do cu ment s", intent_router=IntentRouter())

    assert interpretation.normalized_text == "documents kholo"
    assert interpretation.intent.intent_type is IntentType.OPEN_FOLDER
    assert interpretation.intent.metadata["target_name"] == "documents"


def test_spoken_normalizer_repairs_fragmented_desktop_phrase() -> None:
    normalizer = SpokenCommandNormalizer()

    interpretation = normalizer.interpret("des ktop", intent_router=IntentRouter())

    assert interpretation.normalized_text == "desktop kholo"
    assert interpretation.intent.intent_type is IntentType.OPEN_FOLDER
    assert interpretation.intent.metadata["target_name"] == "desktop"


def test_spoken_normalizer_repairs_ava_test_phrase() -> None:
    normalizer = SpokenCommandNormalizer()

    interpretation = normalizer.interpret("Ava Test kholo", intent_router=IntentRouter())

    assert interpretation.normalized_text == "ava-test kholo"
    assert interpretation.intent.intent_type is IntentType.OPEN_FOLDER
    assert interpretation.intent.metadata["target_name"] == "ava-test"


def test_spoken_normalizer_repairs_create_file_collapse() -> None:
    normalizer = SpokenCommandNormalizer()

    interpretation = normalizer.interpret(
        "is fo lder me an while banao",
        intent_router=IntentRouter(),
    )

    assert interpretation.normalized_text == "is folder me new file banao"
    assert interpretation.intent.intent_type is IntentType.CREATE_FILE
    assert interpretation.local_command_like is True


def test_spoken_normalizer_repairs_contextual_rename_collapse() -> None:
    normalizer = SpokenCommandNormalizer()

    interpretation = normalizer.interpret(
        "is fi le bad low phase 4 note",
        intent_router=IntentRouter(),
    )

    assert interpretation.normalized_text == "is file badlo phase 4 note"
    assert interpretation.intent.intent_type is IntentType.RENAME_PATH
    assert interpretation.intent.metadata["new_name"] == "phase 4 note"


def test_spoken_normalizer_repairs_contextual_move_archive_collapse() -> None:
    normalizer = SpokenCommandNormalizer()

    interpretation = normalizer.interpret(
        "is fo lder KO ar chi ve me move.",
        intent_router=IntentRouter(),
    )

    assert interpretation.normalized_text == "is folder ko archive me move"
    assert interpretation.intent.intent_type is IntentType.MOVE_PATH
    assert interpretation.intent.metadata["destination_name"] == "archive"


def test_spoken_normalizer_promotes_observed_folder_rename_collapse() -> None:
    normalizer = SpokenCommandNormalizer()

    interpretation = normalizer.interpret(
        "is fo ld pha se four folder.",
        intent_router=IntentRouter(),
    )

    assert interpretation.normalized_text == "is folder badlo phase four folder"
    assert interpretation.intent.intent_type is IntentType.RENAME_PATH
    assert interpretation.intent.metadata["new_name"] == "phase four folder"


def test_spoken_normalizer_repairs_han_confirmation_phrase() -> None:
    normalizer = SpokenCommandNormalizer()

    interpretation = normalizer.interpret("Han.", intent_router=IntentRouter())

    assert interpretation.normalized_text == "haan"
    assert interpretation.intent.intent_type is IntentType.CONFIRM


def test_spoken_normalizer_repairs_han_confirmation_with_noise() -> None:
    normalizer = SpokenCommandNormalizer()

    interpretation = normalizer.interpret("Han. <noise>", intent_router=IntentRouter())

    assert interpretation.normalized_text == "haan"
    assert interpretation.intent.intent_type is IntentType.CONFIRM


def test_spoken_normalizer_repairs_fragmented_window_maximize_phrase() -> None:
    normalizer = SpokenCommandNormalizer()

    interpretation = normalizer.interpret("is Wi ndow KO max imi ze", intent_router=IntentRouter())

    assert interpretation.normalized_text == "is window ko maximize"
    assert interpretation.intent.intent_type is IntentType.MAXIMIZE_WINDOW


def test_spoken_normalizer_repairs_fragmented_focus_current_app_phrase() -> None:
    normalizer = SpokenCommandNormalizer()

    interpretation = normalizer.interpret("is up par fo cus caro", intent_router=IntentRouter())

    assert interpretation.normalized_text == "is app par focus karo"
    assert interpretation.intent.intent_type is IntentType.FOCUS_APP
    assert interpretation.intent.metadata["use_active_app_context"] == "true"


def test_spoken_normalizer_repairs_fragmented_next_window_phrase() -> None:
    normalizer = SpokenCommandNormalizer()

    interpretation = normalizer.interpret("Ne xt wi ndow", intent_router=IntentRouter())

    assert interpretation.normalized_text == "next window"
    assert interpretation.intent.intent_type is IntentType.NEXT_WINDOW


def test_spoken_normalizer_requests_confirmation_for_long_search_query() -> None:
    normalizer = SpokenCommandNormalizer()

    interpretation = normalizer.interpret(
        "YouTube par lo fi hip hop playlist search karo",
        intent_router=IntentRouter(),
    )

    assert interpretation.intent.intent_type is IntentType.SEARCH_YOUTUBE
    assert interpretation.intent.metadata["query"] == "lofi hip hop playlist"
    assert interpretation.needs_confirmation is True
    assert (
        interpretation.confirmation_prompt == "Ye search query `lofi hip hop playlist` sahi hai na?"
    )


def test_spoken_normalizer_preserves_compound_youtube_open_and_search_phrase() -> None:
    normalizer = SpokenCommandNormalizer()

    interpretation = normalizer.interpret(
        "YouTube kholo aur lofi hip hop playlist search karo",
        intent_router=IntentRouter(),
    )

    assert interpretation.normalized_text == "youtube par lofi hip hop playlist search karo"
    assert interpretation.intent.intent_type is IntentType.SEARCH_YOUTUBE
    assert interpretation.intent.metadata["query"] == "lofi hip hop playlist"
    assert interpretation.intent.metadata["compound_open_first"] == "true"
    assert interpretation.needs_confirmation is False


def test_spoken_normalizer_suggests_known_domain_for_ambiguous_domain() -> None:
    normalizer = SpokenCommandNormalizer()

    interpretation = normalizer.interpret("hub dot com kholo", intent_router=IntentRouter())

    assert interpretation.normalized_text == "github.com kholo"
    assert interpretation.intent.intent_type is IntentType.OPEN_WEBSITE
    assert interpretation.intent.metadata["url"] == "https://github.com"
    assert interpretation.needs_confirmation is True
    assert interpretation.confirmation_prompt == "Aap `github.com` bol rahe the na?"


def test_spoken_normalizer_repairs_fragmented_youtube_search_phrase() -> None:
    normalizer = SpokenCommandNormalizer()

    interpretation = normalizer.interpret(
        "YouTu be p a r lop fy hi p hop pla ylist se arch",
        intent_router=IntentRouter(),
    )

    assert interpretation.intent.intent_type is IntentType.SEARCH_YOUTUBE
    assert interpretation.intent.metadata["query"] == "lofi hip hop playlist"
    assert interpretation.needs_confirmation is True
    assert (
        interpretation.confirmation_prompt == "Ye search query `lofi hip hop playlist` sahi hai na?"
    )


def test_spoken_normalizer_repairs_observed_youtube_search_collapse() -> None:
    normalizer = SpokenCommandNormalizer()

    interpretation = normalizer.recover_browser_command(
        raw_text="You Tube hi p hop play list sear ch.",
        model_text="",
        intent_router=IntentRouter(),
    )

    assert interpretation is not None
    assert interpretation.normalized_text == "youtube par lofi hip hop playlist search karo"
    assert interpretation.intent.intent_type is IntentType.SEARCH_YOUTUBE
    assert interpretation.intent.metadata["query"] == "lofi hip hop playlist"
    assert interpretation.needs_confirmation is True
    assert (
        interpretation.confirmation_prompt == "Ye search query `lofi hip hop playlist` sahi hai na?"
    )


def test_spoken_normalizer_recovers_browser_command_from_model_output() -> None:
    normalizer = SpokenCommandNormalizer()

    interpretation = normalizer.recover_browser_command(
        raw_text=". com",
        model_text="Sure, opening GitHub for you.",
        intent_router=IntentRouter(),
    )

    assert interpretation is not None
    assert interpretation.normalized_text == "github.com kholo"
    assert interpretation.intent.intent_type is IntentType.OPEN_WEBSITE
    assert interpretation.needs_confirmation is True
    assert interpretation.confirmation_prompt == "Aap `github.com` bol rahe the na?"


def test_spoken_normalizer_recovers_youtube_search_from_model_output() -> None:
    normalizer = SpokenCommandNormalizer()

    interpretation = normalizer.recover_browser_command(
        raw_text="YouTu be p a r lop fy hi p hop pla ylist se arch.",
        model_text='Sure, searching "lofi hip hop playlist" on YouTube.',
        intent_router=IntentRouter(),
    )

    assert interpretation is not None
    assert interpretation.normalized_text == "youtube par lofi hip hop playlist search karo"
    assert interpretation.intent.intent_type is IntentType.SEARCH_YOUTUBE
    assert interpretation.needs_confirmation is True
    assert (
        interpretation.confirmation_prompt == "Ye search query `lofi hip hop playlist` sahi hai na?"
    )
