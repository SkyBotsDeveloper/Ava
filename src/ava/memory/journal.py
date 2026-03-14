from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ava.memory.models import ActionJournalEntry
from ava.safety.policy import ConfirmationStatus, ResultStatus


@dataclass(slots=True)
class JournalRow:
    id: int
    command_text: str
    action_name: str
    confirmation_status: str
    result_status: str
    source: str
    created_at: datetime
    details: dict[str, Any] | None


class ActionJournalStore:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def record_action(
        self,
        *,
        command_text: str,
        action_name: str,
        confirmation_status: ConfirmationStatus,
        result_status: ResultStatus,
        source: str,
        details: dict[str, Any] | None = None,
    ) -> int:
        with self.session_factory.begin() as session:
            entry = ActionJournalEntry(
                command_text=command_text,
                action_name=action_name,
                confirmation_status=confirmation_status.value,
                result_status=result_status.value,
                source=source,
                created_at=datetime.now(UTC),
                details=details,
            )
            session.add(entry)
            session.flush()
            return int(entry.id)

    def list_recent(self, limit: int = 20) -> list[JournalRow]:
        query = (
            select(ActionJournalEntry).order_by(ActionJournalEntry.created_at.desc()).limit(limit)
        )
        with self.session_factory() as session:
            rows = session.scalars(query).all()
        return [
            JournalRow(
                id=int(row.id),
                command_text=row.command_text,
                action_name=row.action_name,
                confirmation_status=row.confirmation_status,
                result_status=row.result_status,
                source=row.source,
                created_at=row.created_at,
                details=row.details,
            )
            for row in rows
        ]
