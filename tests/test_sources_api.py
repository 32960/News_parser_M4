from __future__ import annotations


HABR_URL = "https://habr.com/ru/rss/articles/"


def test_create_habr_source_201(client):
    response = client.post(
        "/api/sources/",
        json={
            "type": "site",
            "name": "Habr",
            "url": HABR_URL,
            "enabled": True,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Habr"
    assert body["url"] == HABR_URL
    assert body["enabled"] is True


def test_unsupported_site_url_422(client):
    response = client.post(
        "/api/sources/",
        json={
            "type": "site",
            "name": "Unknown",
            "url": "https://example.com/news",
            "enabled": True,
        },
    )
    assert response.status_code == 422
    assert "Unsupported" in response.json()["detail"]


def test_delete_source_with_news_409(client, habr_source, news_item):
    response = client.delete(f"/api/sources/{habr_source.id}/")
    assert response.status_code == 409
