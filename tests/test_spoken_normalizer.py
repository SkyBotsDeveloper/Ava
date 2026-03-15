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
