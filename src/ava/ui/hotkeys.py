from __future__ import annotations

import ctypes
import logging
import sys
from dataclasses import dataclass
from typing import ClassVar, Final

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal

logger = logging.getLogger(__name__)

_WM_HOTKEY: Final = 0x0312
_MOD_ALT: Final = 0x0001
_MOD_CONTROL: Final = 0x0002
_MOD_SHIFT: Final = 0x0004
_MOD_WIN: Final = 0x0008
_MOD_NOREPEAT: Final = 0x4000

_VK_CODES: Final[dict[str, int]] = {
    "a": 0x41,
    "m": 0x4D,
    "backspace": 0x08,
}
_MODIFIER_CODES: Final[dict[str, int]] = {
    "alt": _MOD_ALT,
    "ctrl": _MOD_CONTROL,
    "control": _MOD_CONTROL,
    "shift": _MOD_SHIFT,
    "win": _MOD_WIN,
    "meta": _MOD_WIN,
}


class _WinMsg(ctypes.Structure):
    _fields_: ClassVar[list[tuple[str, object]]] = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_size_t),
        ("lParam", ctypes.c_size_t),
        ("time", ctypes.c_uint),
        ("pt_x", ctypes.c_long),
        ("pt_y", ctypes.c_long),
        ("lPrivate", ctypes.c_uint),
    ]


@dataclass(slots=True, frozen=True)
class ParsedHotkey:
    modifiers: int
    virtual_key: int


def parse_hotkey(spec: str) -> ParsedHotkey:
    tokens = [token.strip().lower() for token in spec.split("+") if token.strip()]
    if not tokens:
        raise ValueError("Hotkey spec cannot be empty.")

    modifiers = _MOD_NOREPEAT
    virtual_key: int | None = None

    for token in tokens:
        if token in _MODIFIER_CODES:
            modifiers |= _MODIFIER_CODES[token]
            continue
        if virtual_key is not None:
            raise ValueError(f"Hotkey spec `{spec}` contains multiple keys.")
        if token not in _VK_CODES:
            raise ValueError(f"Hotkey token `{token}` is not supported.")
        virtual_key = _VK_CODES[token]

    if virtual_key is None:
        raise ValueError(f"Hotkey spec `{spec}` is missing a key.")
    return ParsedHotkey(modifiers=modifiers, virtual_key=virtual_key)


class GlobalHotkeyManager(QObject, QAbstractNativeEventFilter):
    manualTriggerRequested = Signal()
    muteRequested = Signal()
    cancelRequested = Signal()

    def __init__(self) -> None:
        QObject.__init__(self)
        QAbstractNativeEventFilter.__init__(self)
        self._registered_ids: set[int] = set()
        self._hotkey_handlers: dict[int, Signal] = {}
        self._user32 = (
            ctypes.WinDLL("user32", use_last_error=True) if sys.platform == "win32" else None
        )

    @property
    def supported(self) -> bool:
        return self._user32 is not None

    def register_defaults(self, *, push_to_talk: str, mute: str, cancel: str) -> dict[str, bool]:
        if not self.supported:
            logger.info(
                "Skipping global hotkey registration on non-Windows platform",
                extra={"event": "global_hotkeys_unsupported"},
            )
            return {"push_to_talk": False, "mute": False, "cancel": False}

        return {
            "push_to_talk": self._register_hotkey(1, push_to_talk, self.manualTriggerRequested),
            "mute": self._register_hotkey(2, mute, self.muteRequested),
            "cancel": self._register_hotkey(3, cancel, self.cancelRequested),
        }

    def unregister_all(self) -> None:
        if not self.supported:
            return
        for hotkey_id in tuple(self._registered_ids):
            self._user32.UnregisterHotKey(None, hotkey_id)
            self._registered_ids.discard(hotkey_id)
        self._hotkey_handlers.clear()
        logger.info(
            "Global hotkeys unregistered",
            extra={"event": "global_hotkeys_unregistered"},
        )

    def nativeEventFilter(self, event_type, message):  # type: ignore[override]
        if not self.supported:
            return False, 0
        if event_type not in {b"windows_generic_MSG", b"windows_dispatcher_MSG"}:
            return False, 0

        msg = _WinMsg.from_address(int(message))
        if msg.message != _WM_HOTKEY:
            return False, 0

        hotkey_id = int(msg.wParam)
        signal = self._hotkey_handlers.get(hotkey_id)
        if signal is None:
            return False, 0

        logger.info(
            "Global hotkey triggered",
            extra={"event": "global_hotkey_triggered", "hotkey_id": hotkey_id},
        )
        signal.emit()
        return True, 0

    def _register_hotkey(self, hotkey_id: int, spec: str, signal: Signal) -> bool:
        parsed = parse_hotkey(spec)
        used_norepeat = True
        ctypes.set_last_error(0)
        registered = bool(
            self._user32.RegisterHotKey(
                None,
                hotkey_id,
                parsed.modifiers,
                parsed.virtual_key,
            )
        )
        error_code = ctypes.get_last_error()
        if not registered and parsed.modifiers & _MOD_NOREPEAT:
            ctypes.set_last_error(0)
            fallback_modifiers = parsed.modifiers & ~_MOD_NOREPEAT
            used_norepeat = False
            registered = bool(
                self._user32.RegisterHotKey(
                    None,
                    hotkey_id,
                    fallback_modifiers,
                    parsed.virtual_key,
                )
            )
            error_code = ctypes.get_last_error()
        if not registered:
            logger.warning(
                "Failed to register global hotkey",
                extra={
                    "event": "global_hotkey_registration_failed",
                    "hotkey_id": hotkey_id,
                    "hotkey_spec": spec,
                    "error_code": error_code,
                },
            )
            return False

        self._registered_ids.add(hotkey_id)
        self._hotkey_handlers[hotkey_id] = signal
        logger.info(
            "Global hotkey registered",
            extra={
                "event": "global_hotkey_registered",
                "hotkey_id": hotkey_id,
                "hotkey_spec": spec,
                "used_norepeat": used_norepeat,
            },
        )
        return True
