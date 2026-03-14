from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal

from ava.app.state import AssistantState
from ava.config.settings import Settings


class QtAssistantState(QObject):
    statusChanged = Signal()
    mutedChanged = Signal()
    lastCommandChanged = Signal()
    lastResponseChanged = Signal()

    hotkeysChanged = Signal()

    def __init__(self, state: AssistantState, settings: Settings) -> None:
        super().__init__()
        self._state = state
        self._settings = settings

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._state.status.value

    @Property(bool, notify=mutedChanged)
    def muted(self) -> bool:
        return self._state.muted

    @Property(str, notify=lastCommandChanged)
    def lastCommand(self) -> str:
        return self._state.last_command

    @Property(str, notify=lastResponseChanged)
    def lastResponse(self) -> str:
        return self._state.last_response

    @Property(str, notify=hotkeysChanged)
    def pushToTalkHotkey(self) -> str:
        return self._settings.push_to_talk_hotkey

    @Property(str, notify=hotkeysChanged)
    def muteHotkey(self) -> str:
        return self._settings.mute_hotkey

    @Property(str, notify=hotkeysChanged)
    def emergencyStopHotkey(self) -> str:
        return self._settings.emergency_stop_hotkey

    def sync(self) -> None:
        self.statusChanged.emit()
        self.mutedChanged.emit()
        self.lastCommandChanged.emit()
        self.lastResponseChanged.emit()
        self.hotkeysChanged.emit()
