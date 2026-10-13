from __future__ import annotations

from app.models import Post, PostStatus
from app.utils import utc_now


def test_list_posts_and_filter_by_status(
    client, session, news_item, generated_post, published_post
):
    all_posts = client.get("/api/posts/")
    assert all_posts.status_code == 200
    assert len(all_posts.json()) >= 2

    generated_only = client.get("/api/posts/", params={"status": "generated"})
    assert generated_only.status_code == 200
    body = generated_only.json()
    assert body
    assert all(item["status"] == "generated" for item in body)


def test_get_post(client, generated_post):
    response = client.get(f"/api/posts/{generated_post.id}/")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(generated_post.id)
    assert body["status"] == "generated"
    assert body["news_item"]["id"] is not None


def test_get_unknown_post_404(client):
    response = client.get(
        "/api/posts/00000000-0000-0000-0000-000000000099/"
    )
    assert response.status_code == 404


def test_publish_after_publication_failed_returns_202(
    client, session, news_item
):
    post = Post(
        news_item_id=news_item.id,
        status=PostStatus.PUBLICATION_FAILED,
        generated_text="Retry me",
        generated_at=utc_now(),
        published_at=None,
    )
    session.add(post)
    session.commit()
    session.refresh(post)

    response = client.post(f"/api/posts/{post.id}/publish/")
    assert response.status_code == 202
    assert response.json()["post_id"] == str(post.id)
