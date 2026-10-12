from __future__ import annotations

from datetime import timedelta

from app.models import NewsItem, Post, PostStatus
from app.utils import utc_now


def test_stats_totals_and_per_source(
    client, session, habr_source, news_item, generated_post, published_post
):
    failed = Post(
        news_item_id=news_item.id,
        status=PostStatus.GENERATION_FAILED,
    )
    session.add(failed)

    older = utc_now() - timedelta(hours=3)
    newer = utc_now() - timedelta(hours=1)
    news_item.collected_at = older
    session.add(news_item)

    second = NewsItem(
        title="Second news",
        url="https://habr.com/ru/articles/456/",
        raw_text="Another article body for stats.",
        source_id=habr_source.id,
        collected_at=newer,
    )
    session.add(second)
    session.commit()

    response = client.get("/api/stats/")
    assert response.status_code == 200
    body = response.json()

    assert body["collected"] == 2
    # generated_post + published_post (failed does not count as generated)
    assert body["generated"] == 2
    assert body["published"] == 1
    assert body["generation_failed"] == 1
    assert body["publication_failed"] == 0

    assert len(body["sources"]) == 1
    source = body["sources"][0]
    assert source["id"] == str(habr_source.id)
    assert source["name"] == "Habr"
    assert source["news_count"] == 2
    assert source["generated"] == 2
    assert source["published"] == 1
    assert source["generation_failed"] == 1
    assert source["last_successful_collection_at"] is not None


def test_stats_empty(client):
    response = client.get("/api/stats/")
    assert response.status_code == 200
    body = response.json()
    assert body["collected"] == 0
    assert body["generated"] == 0
    assert body["published"] == 0
    assert body["sources"] == []
