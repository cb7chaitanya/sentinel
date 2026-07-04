import uuid

import httpx
from fastapi.testclient import TestClient
from gateway.core.di import get_http_client
from gateway.main import app

WAREHOUSE_ID = uuid.uuid4()


def _client_returning(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_get_warehouse_state_proxies_memory_service() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/state/{WAREHOUSE_ID}"
        return httpx.Response(200, json={"warehouse_id": str(WAREHOUSE_ID), "entities": []})

    app.dependency_overrides[get_http_client] = lambda: _client_returning(handler)
    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/state/{WAREHOUSE_ID}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["warehouse_id"] == str(WAREHOUSE_ID)


def test_get_warehouse_state_passes_as_of_through() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["as_of"] = request.url.params.get("as_of", "")
        return httpx.Response(200, json={"warehouse_id": str(WAREHOUSE_ID)})

    app.dependency_overrides[get_http_client] = lambda: _client_returning(handler)
    try:
        client = TestClient(app)
        client.get(f"/api/v1/state/{WAREHOUSE_ID}", params={"as_of": "2026-01-01T00:00:00+00:00"})
    finally:
        app.dependency_overrides.clear()

    assert captured["as_of"] == "2026-01-01T00:00:00+00:00"


def test_get_warehouse_state_surfaces_upstream_error_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "not found"})

    app.dependency_overrides[get_http_client] = lambda: _client_returning(handler)
    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/state/{WAREHOUSE_ID}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
