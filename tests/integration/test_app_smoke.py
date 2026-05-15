from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_route() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_home_page_renders() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "SJM Sports Recruiting Portal" in response.text
