from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app import models  # noqa: F401 -- register tables in SQLModel.metadata
from app.config import get_settings

logger = logging.getLogger(__name__)


def _register_sqlite_btrim(dbapi_conn, _connection_record) -> None:
    """Postgres CHECKs use btrim(); SQLite needs a compatible function for tests."""
    dbapi_conn.create_function(
        "btrim",
        1,
        lambda value: value.strip() if value is not None else None,
    )


def create_db_engine(url: str | None = None):
    database_url = url or get_settings().database_url
    if database_url.startswith("sqlite"):
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        event.listen(engine, "connect", _register_sqlite_btrim)
        return engine
    return create_engine(database_url)


engine = create_db_engine()


def open_session() -> Session:
    return Session(engine)


def get_session() -> Generator[Session, None, None]:
    with open_session() as session:
        yield session


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    logger.info("Database initialized")
