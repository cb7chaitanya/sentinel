import httpx
from fastapi.testclient import TestClient
from gateway.core.di import get_http_client
from gateway.main import app


def _client_returning(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_ask_copilot_proxies_agent_service() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/copilot/ask"
        assert b"Where is the pallet?" in request.content
        return httpx.Response(200, json={"answer": "It's in Zone B.", "grounded": True})

    app.dependency_overrides[get_http_client] = lambda: _client_returning(handler)
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/copilot/ask",
            json={
                "warehouse_id": "00000000-0000-0000-0000-000000000000",
                "question": "Where is the pallet?",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["answer"] == "It's in Zone B."


def test_ask_copilot_surfaces_upstream_error_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": "invalid"})

    app.dependency_overrides[get_http_client] = lambda: _client_returning(handler)
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/copilot/ask",
            json={"warehouse_id": "00000000-0000-0000-0000-000000000000", "question": "?"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
