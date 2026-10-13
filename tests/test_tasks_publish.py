from __future__ import annotations

from app.models import Post, PostStatus
from app.tasks import _publish_post, build_publish_message
from app.utils import utc_now


async def _ok_send(_message: str) -> None:
    return None


async def _fail_send(_message: str) -> None:
    raise ConnectionError("Telegram unreachable")


def test_publish_success(task_session, generated_post, monkeypatch):
    monkeypatch.setattr(
        "app.tasks.send_message_to_channel",
        _ok_send,
    )

    result = _publish_post(generated_post.id)
    assert result == generated_post.id

    task_session.refresh(generated_post)
    assert generated_post.status == PostStatus.PUBLISHED
    assert generated_post.published_at is not None


def test_publish_telegram_error_marks_failed(
    task_session, generated_post, monkeypatch
):
    monkeypatch.setattr(
        "app.tasks.send_message_to_channel",
        _fail_send,
    )

    result = _publish_post(generated_post.id)
    assert result is None

    task_session.refresh(generated_post)
    assert generated_post.status == PostStatus.PUBLICATION_FAILED
    assert generated_post.generated_text is not None
    assert generated_post.published_at is None


def test_publish_retry_after_failure(task_session, news_item, monkeypatch):
    post = Post(
        news_item_id=news_item.id,
        status=PostStatus.PUBLICATION_FAILED,
        generated_text="Retry publish text",
        generated_at=utc_now(),
    )
    task_session.add(post)
    task_session.commit()
    task_session.refresh(post)

    monkeypatch.setattr(
        "app.tasks.send_message_to_channel",
        _ok_send,
    )

    result = _publish_post(post.id)
    assert result == post.id
    task_session.refresh(post)
    assert post.status == PostStatus.PUBLISHED


def test_publish_skips_already_published(
    task_session, published_post, monkeypatch
):
    called = {"yes": False}

    async def _track(_message: str) -> None:
        called["yes"] = True

    monkeypatch.setattr("app.tasks.send_message_to_channel", _track)

    result = _publish_post(published_post.id)
    assert result == published_post.id
    assert called["yes"] is False


def test_build_publish_message_appends_url(generated_post, task_session):
    task_session.refresh(generated_post)
    # ensure relationship is available
    _ = generated_post.news_item
    message = build_publish_message(generated_post)
    assert generated_post.generated_text in message
    assert generated_post.news_item.url in message
