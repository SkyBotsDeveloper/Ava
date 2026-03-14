from ava.live.prompting import AVA_SYSTEM_INSTRUCTION


def test_ava_prompt_keeps_hinglish_and_confirmation_rules() -> None:
    assert "Hinglish" in AVA_SYSTEM_INSTRUCTION
    assert "Ye wali ID/contact hai na?" in AVA_SYSTEM_INSTRUCTION
    assert "You do not act on your own randomly." in AVA_SYSTEM_INSTRUCTION
