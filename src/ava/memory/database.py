from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def build_sqlite_url(database_path: Path) -> str:
    return f"sqlite:///{database_path.as_posix()}"


def build_engine(database_path: Path) -> Engine:
    return create_engine(build_sqlite_url(database_path), future=True)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
