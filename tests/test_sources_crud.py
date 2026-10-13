from __future__ import annotations

HABR_URL = "https://habr.com/ru/rss/articles/"


def test_list_and_get_source(client, habr_source):
    listed = client.get("/api/sources/")
    assert listed.status_code == 200
    assert any(item["id"] == str(habr_source.id) for item in listed.json())

    got = client.get(f"/api/sources/{habr_source.id}/")
    assert got.status_code == 200
    assert got.json()["name"] == "Habr"


def test_get_unknown_source_404(client):
    response = client.get(
        "/api/sources/00000000-0000-0000-0000-000000000099/"
    )
    assert response.status_code == 404


def test_patch_disable_source(client, habr_source):
    response = client.patch(
        f"/api/sources/{habr_source.id}/",
        json={"enabled": False},
    )
    assert response.status_code == 200
    assert response.json()["enabled"] is False


def test_patch_unsupported_url_422(client, habr_source):
    response = client.patch(
        f"/api/sources/{habr_source.id}/",
        json={"url": "https://example.com/rss"},
    )
    assert response.status_code == 422


def test_delete_source_without_news_204(client, habr_source):
    response = client.delete(f"/api/sources/{habr_source.id}/")
    assert response.status_code == 204
    assert client.get(f"/api/sources/{habr_source.id}/").status_code == 404


def test_create_telegram_source_normalizes_url(client):
    response = client.post(
        "/api/sources/",
        json={
            "type": "telegram",
            "name": "Durov",
            "url": "@durov",
            "enabled": True,
        },
    )
    assert response.status_code == 201
    assert response.json()["url"] == "https://t.me/durov"


def test_create_habr_source_listed(client):
    created = client.post(
        "/api/sources/",
        json={
            "type": "site",
            "name": "Habr 2",
            "url": HABR_URL,
            "enabled": True,
        },
    )
    assert created.status_code == 201
    listed = client.get("/api/sources/")
    assert any(item["name"] == "Habr 2" for item in listed.json())
