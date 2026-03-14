from ava.ui.hotkeys import parse_hotkey


def test_parse_hotkey_for_push_to_talk() -> None:
    parsed = parse_hotkey("ctrl+alt+a")

    assert parsed.virtual_key == 0x41
    assert parsed.modifiers & 0x0001
    assert parsed.modifiers & 0x0002


def test_parse_hotkey_for_backspace_cancel() -> None:
    parsed = parse_hotkey("ctrl+alt+backspace")

    assert parsed.virtual_key == 0x08
    assert parsed.modifiers & 0x0001
    assert parsed.modifiers & 0x0002
