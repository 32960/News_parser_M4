from __future__ import annotations

from app.models import Post, PostStatus
from app.tasks import generate_post, start_generating


def test_generate_post_success(task_session, news_item, monkeypatch):
    post = Post(news_item_id=news_item.id, status=PostStatus.NEW)
    task_session.add(post)
    task_session.commit()
    task_session.refresh(post)

    monkeypatch.setattr(
        "app.tasks.generate_text",
        lambda text: "AI generated telegram post",
    )

    result = generate_post.run(str(post.id))
    assert result == str(post.id)

    task_session.refresh(post)
    assert post.status == PostStatus.GENERATED
    assert post.generated_text == "AI generated telegram post"
    assert post.generated_at is not None


def test_generate_post_openai_error_marks_failed(
    task_session, news_item, monkeypatch
):
    post = Post(news_item_id=news_item.id, status=PostStatus.NEW)
    task_session.add(post)
    task_session.commit()
    task_session.refresh(post)

    def _boom(_text: str) -> str:
        raise RuntimeError("OpenAI down")

    monkeypatch.setattr("app.tasks.generate_text", _boom)

    result = generate_post.run(str(post.id))
    assert result is None

    task_session.refresh(post)
    assert post.status == PostStatus.GENERATION_FAILED
    assert post.generated_text is None
    assert post.generated_at is None


def test_generate_post_skips_when_source_disabled(
    task_session, news_item, habr_source, monkeypatch
):
    post = Post(news_item_id=news_item.id, status=PostStatus.NEW)
    task_session.add(post)
    habr_source.enabled = False
    task_session.add(habr_source)
    task_session.commit()
    task_session.refresh(post)

    called = {"yes": False}

    def _should_not_run(_text: str) -> str:
        called["yes"] = True
        return "nope"

    monkeypatch.setattr("app.tasks.generate_text", _should_not_run)

    result = generate_post.run(str(post.id))
    assert result is None
    assert called["yes"] is False

    task_session.refresh(post)
    assert post.status == PostStatus.NEW


def test_start_generating_enqueues_delay(
    task_session, news_item, monkeypatch
):
    delayed: list[str] = []

    monkeypatch.setattr(
        "app.tasks.generate_post.delay",
        lambda post_id: delayed.append(str(post_id)),
    )

    post_id = start_generating(task_session, news_item.id)
    assert post_id is not None
    assert delayed == [str(post_id)]

    post = task_session.get(Post, post_id)
    assert post is not None
    assert post.status == PostStatus.NEW


def test_generate_post_rejects_wrong_status(
    task_session, generated_post, monkeypatch
):
    def _should_not_run(_text: str) -> str:
        raise AssertionError("should not call AI")

    monkeypatch.setattr("app.tasks.generate_text", _should_not_run)
    result = generate_post.run(str(generated_post.id))
    assert result is None
