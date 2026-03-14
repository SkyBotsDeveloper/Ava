from __future__ import annotations

from datetime import datetime
from enum import IntEnum

from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, Qt

from ava.memory.journal import ActionJournalStore, JournalRow


class HistoryRoles(IntEnum):
    COMMAND_TEXT = Qt.ItemDataRole.UserRole + 1
    ACTION_NAME = Qt.ItemDataRole.UserRole + 2
    RESULT_STATUS = Qt.ItemDataRole.UserRole + 3
    CONFIRMATION_STATUS = Qt.ItemDataRole.UserRole + 4
    TIMESTAMP = Qt.ItemDataRole.UserRole + 5
    SOURCE = Qt.ItemDataRole.UserRole + 6


class HistoryListModel(QAbstractListModel):
    def __init__(
        self,
        journal: ActionJournalStore,
        limit: int = 3,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._journal = journal
        self._limit = limit
        self._entries: list[JournalRow] = []

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        if parent is None:
            parent = QModelIndex()
        if parent.isValid():
            return 0
        return len(self._entries)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> str | None:
        if not index.isValid():
            return None
        entry = self._entries[index.row()]
        if role == HistoryRoles.COMMAND_TEXT:
            return entry.command_text
        if role == HistoryRoles.ACTION_NAME:
            return entry.action_name
        if role == HistoryRoles.RESULT_STATUS:
            return entry.result_status
        if role == HistoryRoles.CONFIRMATION_STATUS:
            return entry.confirmation_status
        if role == HistoryRoles.TIMESTAMP:
            return self._format_timestamp(entry.created_at)
        if role == HistoryRoles.SOURCE:
            return entry.source
        return None

    def roleNames(self) -> dict[int, bytes]:
        return {
            HistoryRoles.COMMAND_TEXT: b"commandText",
            HistoryRoles.ACTION_NAME: b"actionName",
            HistoryRoles.RESULT_STATUS: b"resultStatus",
            HistoryRoles.CONFIRMATION_STATUS: b"confirmationStatus",
            HistoryRoles.TIMESTAMP: b"timestamp",
            HistoryRoles.SOURCE: b"source",
        }

    def refresh(self) -> None:
        self.beginResetModel()
        self._entries = self._journal.list_recent(self._limit)
        self.endResetModel()

    @staticmethod
    def _format_timestamp(value: datetime) -> str:
        local_value = value.astimezone()
        return local_value.strftime("%H:%M:%S")
