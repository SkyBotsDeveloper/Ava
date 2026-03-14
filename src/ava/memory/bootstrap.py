from __future__ import annotations

from sqlalchemy import Engine

from ava.memory.models import Base


def initialize_database(engine: Engine) -> None:
    Base.metadata.create_all(engine)
