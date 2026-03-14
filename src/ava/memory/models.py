from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ActionJournalEntry(Base):
    __tablename__ = "action_journal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    command_text: Mapped[str] = mapped_column(Text, nullable=False)
    action_name: Mapped[str] = mapped_column(String(128), nullable=False)
    confirmation_status: Mapped[str] = mapped_column(String(32), nullable=False)
    result_status: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="text")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class ConversationTurn(Base):
    __tablename__ = "conversation_turn"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserPreference(Base):
    __tablename__ = "user_preference"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
