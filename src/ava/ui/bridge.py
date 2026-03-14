from __future__ import annotations

from PySide6.QtCore import QObject, Slot

from ava.app.controller import AvaController
from ava.ui.app_state import QtAssistantState


class UiBridge(QObject):
    def __init__(self, controller: AvaController, app_state: QtAssistantState) -> None:
        super().__init__()
        self.controller = controller
        self.app_state = app_state

    @Slot(str)
    def submitTextCommand(self, raw_text: str) -> None:
        self.controller.handle_text_command(raw_text)
        self.app_state.sync()

    @Slot()
    def toggleMute(self) -> None:
        command = "unmute" if self.controller.state.muted else "mute"
        self.controller.handle_text_command(command)
        self.app_state.sync()

    @Slot()
    def emergencyStop(self) -> None:
        self.controller.handle_text_command("Stop Ava")
        self.app_state.sync()
