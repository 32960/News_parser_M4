from __future__ import annotations

from app.models import Post, PostStatus


def test_generate_for_disabled_source_409(client, session, news_item, habr_source):
    habr_source.enabled = False
    session.add(habr_source)
    session.commit()

    response = client.post(
        "/api/generate/",
        json={"news_id": str(news_item.id)},
    )
    assert response.status_code == 409
    assert "disabled" in response.json()["detail"].lower()


def test_generate_unknown_news_404(client):
    response = client.post(
        "/api/generate/",
        json={"news_id": "00000000-0000-0000-0000-000000000099"},
    )
    assert response.status_code == 404


def test_generate_creates_post_202(client, news_item):
    response = client.post(
        "/api/generate/",
        json={"news_id": str(news_item.id)},
    )
    assert response.status_code == 202
    assert "post_id" in response.json()


def test_publish_new_post_409(client, session, news_item):
    post = Post(news_item_id=news_item.id, status=PostStatus.NEW)
    session.add(post)
    session.commit()
    session.refresh(post)

    response = client.post(f"/api/posts/{post.id}/publish/")
    assert response.status_code == 409


def test_publish_generated_returns_202(client, generated_post):
    response = client.post(f"/api/posts/{generated_post.id}/publish/")
    assert response.status_code == 202
    assert response.json()["post_id"] == str(generated_post.id)


def test_publish_already_published_returns_200(client, published_post):
    response = client.post(f"/api/posts/{published_post.id}/publish/")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(published_post.id)
    assert body["status"] == "published"


def test_parse_returns_202_task_id(client):
    response = client.post("/api/parse/")
    assert response.status_code == 202
    assert "task_id" in response.json()
