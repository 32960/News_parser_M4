from __future__ import annotations

from datetime import timedelta

from app.models import NewsItem, Source, SourceType
from app.utils import utc_now


def _add_news(
    session,
    source: Source,
    *,
    title: str,
    url: str,
    raw_text: str,
    published_at=None,
    collected_at=None,
) -> NewsItem:
    item = NewsItem(
        title=title,
        url=url,
        raw_text=raw_text,
        source_id=source.id,
        published_at=published_at,
        collected_at=collected_at or utc_now(),
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def test_filter_by_keyword(client, session, habr_source):
    _add_news(
        session,
        habr_source,
        title="Python tips",
        url="https://habr.com/ru/articles/1/",
        raw_text="Useful Python article",
    )
    _add_news(
        session,
        habr_source,
        title="Cooking",
        url="https://habr.com/ru/articles/2/",
        raw_text="How to bake bread",
    )

    response = client.get("/api/news/", params={"q": "python"})
    assert response.status_code == 200
    titles = {item["title"] for item in response.json()}
    assert titles == {"Python tips"}


def test_filter_by_language(client, session, habr_source):
    _add_news(
        session,
        habr_source,
        title="Новость на русском",
        url="https://habr.com/ru/articles/10/",
        raw_text="Это длинный текст статьи на русском языке про технологии.",
    )
    _add_news(
        session,
        habr_source,
        title="English headline",
        url="https://habr.com/ru/articles/11/",
        raw_text="This is a longer English article about technology and gadgets.",
    )

    response = client.get("/api/news/", params={"lang": "ru"})
    assert response.status_code == 200
    titles = {item["title"] for item in response.json()}
    assert titles == {"Новость на русском"}


def test_filter_by_max_age_hours(client, session, habr_source):
    now = utc_now()
    _add_news(
        session,
        habr_source,
        title="Fresh",
        url="https://habr.com/ru/articles/20/",
        raw_text="Fresh article body text here",
        published_at=now - timedelta(hours=2),
    )
    _add_news(
        session,
        habr_source,
        title="Old",
        url="https://habr.com/ru/articles/21/",
        raw_text="Old article body text here",
        published_at=now - timedelta(hours=48),
    )

    response = client.get("/api/news/", params={"max_age_hours": 24})
    assert response.status_code == 200
    titles = {item["title"] for item in response.json()}
    assert titles == {"Fresh"}


def test_filters_can_be_combined(client, session, habr_source):
    now = utc_now()
    _add_news(
        session,
        habr_source,
        title="Fresh Python",
        url="https://habr.com/ru/articles/40/",
        raw_text="Fresh Python article body about APIs.",
        published_at=now - timedelta(hours=1),
    )
    _add_news(
        session,
        habr_source,
        title="Old Python",
        url="https://habr.com/ru/articles/41/",
        raw_text="Old Python article body about APIs.",
        published_at=now - timedelta(hours=72),
    )

    response = client.get(
        "/api/news/",
        params={"q": "Python", "max_age_hours": 24},
    )
    assert response.status_code == 200
    titles = {item["title"] for item in response.json()}
    assert titles == {"Fresh Python"}


def test_filter_by_source_id(client, session, habr_source):
    verge = Source(
        type=SourceType.SITE,
        name="The Verge",
        url="https://www.theverge.com/rss/index.xml",
        enabled=True,
    )
    session.add(verge)
    session.commit()
    session.refresh(verge)

    _add_news(
        session,
        habr_source,
        title="Habr item",
        url="https://habr.com/ru/articles/30/",
        raw_text="Habr body text for filter test",
    )
    _add_news(
        session,
        verge,
        title="Verge item",
        url="https://www.theverge.com/2026/1/1/test",
        raw_text="Verge body text for filter test",
    )

    response = client.get(
        "/api/news/", params={"source_id": str(verge.id)}
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["title"] == "Verge item"
    assert body[0]["source_id"] == str(verge.id)
