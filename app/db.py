from typing import Generator

from sqlmodel import create_engine, Session, SQLModel

from app.config import get_settings

engine = create_engine(get_settings().database_url)

def open_session() -> Session:
    return Session(engine)


def get_session() -> Generator[Session, None, None]:
    with open_session() as session:
        yield session


def init_db():
    SQLModel.metadata.create_all(engine)
