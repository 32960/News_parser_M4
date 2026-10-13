from __future__ import annotations

from uuid import UUID

from sqlmodel import select

from app.models import NewsItem, Post
from app.tasks import parse_sources
from app.utils import utc_now


class _FakeParser:
    def __init__(self, articles: list[dict]):
        self._articles = articles

    async def parse(self, url: str, limit: int = 10) -> list[dict]:
        return list(self._articles)


def test_parse_sources_creates_news_and_starts_generation(
    task_session, habr_source, monkeypatch
):
    article = {
        "title": "Parsed from feed",
        "url": "https://habr.com/ru/articles/777/",
        "raw_text": "Body collected by fake parser.",
        "summary": None,
        "published_at": None,
        "collected_at": utc_now(),
    }
    delayed: list[str] = []

    monkeypatch.setattr(
        "app.tasks.get_parser",
        lambda source_type, url: _FakeParser([article]),
    )
    monkeypatch.setattr(
        "app.tasks.generate_post.delay",
        lambda post_id: delayed.append(str(post_id)),
    )

    total = parse_sources.run()
    assert total == 1
    assert len(delayed) == 1

    news = task_session.exec(
        select(NewsItem).where(
            NewsItem.url == "https://habr.com/ru/articles/777/"
        )
    ).first()
    assert news is not None
    assert news.source_id == habr_source.id

    post = task_session.get(Post, UUID(delayed[0]))
    assert post is not None
    assert post.news_item_id == news.id


def test_parse_sources_continues_when_one_source_fails(
    task_session, habr_source, monkeypatch
):
    class _BoomParser:
        async def parse(self, url: str, limit: int = 10) -> list[dict]:
            raise RuntimeError("site down")

    monkeypatch.setattr(
        "app.tasks.get_parser",
        lambda source_type, url: _BoomParser(),
    )
    monkeypatch.setattr(
        "app.tasks.generate_post.delay",
        lambda post_id: None,
    )

    total = parse_sources.run()
    assert total == 0
