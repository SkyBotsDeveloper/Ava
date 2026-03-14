from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal

from ava.app.state import AssistantState


class QtAssistantState(QObject):
    statusChanged = Signal()
    mutedChanged = Signal()
    lastCommandChanged = Signal()
    lastResponseChanged = Signal()

    def __init__(self, state: AssistantState) -> None:
        super().__init__()
        self._state = state

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

    def sync(self) -> None:
        self.statusChanged.emit()
        self.mutedChanged.emit()
        self.lastCommandChanged.emit()
        self.lastResponseChanged.emit()
