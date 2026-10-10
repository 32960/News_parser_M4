from __future__ import annotations

from app.services.news_service import NewsService
from app.utils import utc_now


def test_duplicate_url_is_skipped(session, habr_source):
    article = {
        "title": "One",
        "url": "https://habr.com/ru/articles/999/",
        "raw_text": "Body text for the article.",
        "source_id": habr_source.id,
        "collected_at": utc_now(),
    }
    first = NewsService.create(session, article)
    second = NewsService.create(session, article)

    assert first is not None
    assert second is None


def test_duplicate_telegram_ids_are_skipped(session, habr_source):
    # Reuse any source row; identity for TG news is channel+message ids
    article = {
        "title": "TG message",
        "url": None,
        "raw_text": "Hello from channel",
        "telegram_channel_id": -100123,
        "telegram_message_id": 42,
        "source_id": habr_source.id,
        "collected_at": utc_now(),
    }
    first = NewsService.create(session, article)
    second = NewsService.create(session, dict(article))

    assert first is not None
    assert second is None
