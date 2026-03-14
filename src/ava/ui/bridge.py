from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Slot

from ava.app.controller import AvaController
from ava.app.state import AssistantStatus
from ava.intents.models import IntentType
from ava.ui.app_state import QtAssistantState
from ava.ui.history_model import HistoryListModel


class UiBridge(QObject):
    def __init__(
        self,
        controller: AvaController,
        app_state: QtAssistantState,
        history_model: HistoryListModel,
    ) -> None:
        super().__init__()
        self.controller = controller
        self.app_state = app_state
        self.history_model = history_model
        self._pending_command: str | None = None
        self._command_focused = False

        self._thinking_timer = QTimer(self)
        self._thinking_timer.setSingleShot(True)
        self._thinking_timer.timeout.connect(self._process_pending_command)

        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.timeout.connect(self._restore_idle_or_listening)

        self.history_model.refresh()

    @Slot(str)
    def submitTextCommand(self, raw_text: str) -> None:
        cleaned = raw_text.strip()
        if not cleaned:
            self.controller.handle_text_command(cleaned)
            self.app_state.sync()
            return

        parsed_intent = self.controller.intent_router.parse(cleaned)
        if parsed_intent.intent_type in {IntentType.CANCEL, IntentType.MUTE, IntentType.UNMUTE}:
            self._thinking_timer.stop()
            self._idle_timer.stop()
            self._pending_command = None
            self.controller.handle_text_command(cleaned)
            self.history_model.refresh()
            self.app_state.sync()
            return

        self._pending_command = cleaned
        self.controller.state.status = AssistantStatus.THINKING
        self.app_state.sync()
        self._thinking_timer.start(180)

    @Slot()
    def toggleMute(self) -> None:
        command = "unmute" if self.controller.state.muted else "mute"
        self.controller.handle_text_command(command)
        self.history_model.refresh()
        self.app_state.sync()

    @Slot()
    def emergencyStop(self) -> None:
        self._thinking_timer.stop()
        self._idle_timer.stop()
        self._pending_command = None
        self.controller.handle_text_command("Stop Ava")
        self.history_model.refresh()
        self.app_state.sync()

    @Slot(bool)
    def commandInputFocusChanged(self, active: bool) -> None:
        self._command_focused = active
        if self._thinking_timer.isActive() or self._idle_timer.isActive():
            return
        self.controller.state.status = AssistantStatus.LISTENING if active else AssistantStatus.IDLE
        self.app_state.sync()

    def _process_pending_command(self) -> None:
        if not self._pending_command:
            self._restore_idle_or_listening()
            return

        pending = self._pending_command
        self._pending_command = None
        self.controller.handle_text_command(pending)
        self.history_model.refresh()
        self.controller.state.status = AssistantStatus.SPEAKING
        self.app_state.sync()
        self._idle_timer.start(1400)

    def _restore_idle_or_listening(self) -> None:
        self.controller.state.status = (
            AssistantStatus.LISTENING if self._command_focused else AssistantStatus.IDLE
        )
        self.app_state.sync()
