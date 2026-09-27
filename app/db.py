from typing import Generator

from sqlmodel import create_engine, Session, SQLModel
from app import models  # noqa: F401 -- register tables in SQLModel.metadata
from app.config import get_settings
import logging

engine = create_engine(get_settings().database_url)
logger = logging.getLogger(__name__)

def open_session() -> Session:
    return Session(engine)


def get_session() -> Generator[Session, None, None]:
    with open_session() as session:
        yield session


def init_db():
    SQLModel.metadata.create_all(engine)
    logger.info("Database initialized")
