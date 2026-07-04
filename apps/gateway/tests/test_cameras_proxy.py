import uuid

import httpx
from fastapi.testclient import TestClient
from gateway.core.di import get_http_client
from gateway.main import app

CAMERA_ID = uuid.uuid4()


def _client_returning(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_list_camera_streams_proxies_ingestion_service() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/streams"
        return httpx.Response(200, json=[{"camera_id": str(CAMERA_ID), "state": "connected"}])

    app.dependency_overrides[get_http_client] = lambda: _client_returning(handler)
    try:
        client = TestClient(app)
        response = client.get("/api/v1/cameras/streams")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()[0]["camera_id"] == str(CAMERA_ID)


def test_camera_mjpeg_streams_upstream_bytes() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/api/v1/streams/{CAMERA_ID}/mjpeg"
        return httpx.Response(
            200,
            headers={"content-type": "multipart/x-mixed-replace; boundary=sentinelframe"},
            content=b"--sentinelframe\r\nContent-Type: image/jpeg\r\n\r\nJPEGDATA\r\n",
        )

    app.dependency_overrides[get_http_client] = lambda: _client_returning(handler)
    try:
        with TestClient(app) as client, client.stream(
            "GET", f"/api/v1/cameras/{CAMERA_ID}/mjpeg"
        ) as response:
            assert response.status_code == 200
            assert "multipart/x-mixed-replace" in response.headers["content-type"]
            body = b"".join(response.iter_bytes())
    finally:
        app.dependency_overrides.clear()

    assert b"JPEGDATA" in body


def test_camera_mjpeg_404_for_unknown_camera() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "no configured stream"})

    app.dependency_overrides[get_http_client] = lambda: _client_returning(handler)
    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/cameras/{CAMERA_ID}/mjpeg")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
