from __future__ import annotations

import os
from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

# Must be set before importing app.* (Settings + engine read env at import time)
_TEST_ENV = {
    "DATABASE_URL": "sqlite://",
    "CELERY_BROKER_URL": "redis://localhost:6379/0",
    "CELERY_RESULT_BACKEND": "redis://localhost:6379/1",
    "TELEGRAM_SESSION_PATH": "telegram_sessions/test-session",
    "TELEGRAM_API_ID": "1",
    "TELEGRAM_API_HASH": "testhash",
    "TELEGRAM_TARGET_CHANNEL": "@test_channel",
    "OPENAI_API_KEY": "test-key",
    "OPENAI_MODEL": "gpt-test",
}
os.environ.update(_TEST_ENV)

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.db import create_db_engine, get_session  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import NewsItem, Post, PostStatus, Source, SourceType  # noqa: E402
from app.utils import utc_now  # noqa: E402

FAKE_TASK_ID = UUID("00000000-0000-0000-0000-000000000001")


class _FakeAsyncResult:
    id = str(FAKE_TASK_ID)


@pytest.fixture()
def engine():
    eng = create_db_engine("sqlite://")
    SQLModel.metadata.create_all(eng)
    yield eng
    SQLModel.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture()
def session(engine) -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


@pytest.fixture()
def client(session: Session, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    # Celery must not talk to Redis during API tests
    monkeypatch.setattr(
        "app.services.task_service.parse_sources.delay",
        lambda *args, **kwargs: _FakeAsyncResult(),
    )
    monkeypatch.setattr(
        "app.services.task_service.publish_post.delay",
        lambda *args, **kwargs: _FakeAsyncResult(),
    )
    monkeypatch.setattr(
        "app.tasks.generate_post.delay",
        lambda *args, **kwargs: _FakeAsyncResult(),
    )

    application = create_app()

    def _override_session() -> Generator[Session, None, None]:
        yield session

    application.dependency_overrides[get_session] = _override_session

    with TestClient(application) as test_client:
        yield test_client

    application.dependency_overrides.clear()


@pytest.fixture()
def habr_source(session: Session) -> Source:
    source = Source(
        type=SourceType.SITE,
        name="Habr",
        url="https://habr.com/ru/rss/articles/",
        enabled=True,
    )
    session.add(source)
    session.commit()
    session.refresh(source)
    return source


@pytest.fixture()
def news_item(session: Session, habr_source: Source) -> NewsItem:
    item = NewsItem(
        title="Test news",
        url="https://habr.com/ru/articles/123/",
        raw_text="Interesting article about Python and APIs.",
        source_id=habr_source.id,
        collected_at=utc_now(),
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@pytest.fixture()
def generated_post(session: Session, news_item: NewsItem) -> Post:
    post = Post(
        news_item_id=news_item.id,
        status=PostStatus.GENERATED,
        generated_text="Short post for Telegram",
        generated_at=utc_now(),
    )
    session.add(post)
    session.commit()
    session.refresh(post)
    return post


@pytest.fixture()
def published_post(session: Session, news_item: NewsItem) -> Post:
    post = Post(
        news_item_id=news_item.id,
        status=PostStatus.PUBLISHED,
        generated_text="Already published post",
        generated_at=utc_now(),
        published_at=utc_now(),
    )
    session.add(post)
    session.commit()
    session.refresh(post)
    return post
