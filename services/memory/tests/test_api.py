import uuid
from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient
from memory.core.di import get_db_session
from memory.main import app
from sentinel_common.db.session import build_engine
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.conftest import TEST_DATABASE_URL

_TABLES = ("zone_occupancy", "alerts", "events", "entities", "cameras")

WAREHOUSE_ID = uuid.uuid4()
CAMERA_ID = uuid.uuid4()
ZONE_ID = uuid.uuid4()
T0 = "2026-01-01T00:00:00Z"


@pytest.fixture
def client() -> TestClient:
    engine = build_engine(TEST_DATABASE_URL)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as db_session:
            yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
async def _clean_tables() -> AsyncIterator[None]:
    yield
    engine = build_engine(TEST_DATABASE_URL)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as db_session:
        for table in _TABLES:
            await db_session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        await db_session.commit()
    await engine.dispose()


def test_record_observation_then_get_current_state(client: TestClient) -> None:
    response = client.post(
        "/api/v1/observations",
        json={
            "warehouse_id": str(WAREHOUSE_ID),
            "camera_id": str(CAMERA_ID),
            "track_id": 1,
            "label": "forklift",
            "bounding_box": {"x_min": 0, "y_min": 0, "x_max": 10, "y_max": 10},
            "observed_at": T0,
        },
    )
    assert response.status_code == 201
    entity_id = response.json()["id"]

    state_response = client.get(f"/api/v1/state/{WAREHOUSE_ID}", params={"as_of": T0})
    assert state_response.status_code == 200
    body = state_response.json()
    assert len(body["entities"]) == 1
    assert body["entities"][0]["id"] == entity_id
    assert body["entities"][0]["entity_type"] == "forklift"


def test_get_entity_history_404_for_unknown_entity(client: TestClient) -> None:
    response = client.get(f"/api/v1/entities/{uuid.uuid4()}/history")
    assert response.status_code == 404


def test_zone_transition_requires_a_known_entity(client: TestClient) -> None:
    response = client.post(
        "/api/v1/zone-transitions",
        json={
            "warehouse_id": str(WAREHOUSE_ID),
            "zone_id": str(ZONE_ID),
            "zone_name": "Loading Dock",
            "camera_id": str(CAMERA_ID),
            "track_id": 1,
            "kind": "entered",
            "occurred_at": T0,
        },
    )
    assert response.status_code == 404


def test_full_round_trip_observation_zone_event_and_history(client: TestClient) -> None:
    obs = client.post(
        "/api/v1/observations",
        json={
            "warehouse_id": str(WAREHOUSE_ID),
            "camera_id": str(CAMERA_ID),
            "track_id": 5,
            "label": "person",
            "bounding_box": {"x_min": 0, "y_min": 0, "x_max": 10, "y_max": 10},
            "observed_at": T0,
        },
    )
    entity_id = obs.json()["id"]

    zone_response = client.post(
        "/api/v1/zone-transitions",
        json={
            "warehouse_id": str(WAREHOUSE_ID),
            "zone_id": str(ZONE_ID),
            "zone_name": "Loading Dock",
            "camera_id": str(CAMERA_ID),
            "track_id": 5,
            "kind": "entered",
            "occurred_at": T0,
        },
    )
    assert zone_response.status_code == 200

    event_response = client.post(
        "/api/v1/events",
        json={
            "camera_id": str(CAMERA_ID),
            "event_type": "zone_entered",
            "occurred_at": T0,
            "summary": "Worker entered Loading Dock",
            "warehouse_id": str(WAREHOUSE_ID),
            "track_id": 5,
        },
    )
    assert event_response.status_code == 201

    history_response = client.get(f"/api/v1/entities/{entity_id}/history")
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history["zone_occupancy"]) == 1
    assert len(history["events"]) == 1

    events_response = client.get("/api/v1/events", params={"warehouse_id": str(WAREHOUSE_ID)})
    assert events_response.status_code == 200
    assert len(events_response.json()) == 1


def test_alert_lifecycle(client: TestClient) -> None:
    created = client.post(
        "/api/v1/alerts",
        json={"warehouse_id": str(WAREHOUSE_ID), "severity": "high", "summary": "test alert"},
    )
    assert created.status_code == 201
    alert_id = created.json()["id"]
    assert created.json()["status"] == "open"

    acknowledged = client.post(f"/api/v1/alerts/{alert_id}/acknowledge")
    assert acknowledged.status_code == 200
    assert acknowledged.json()["status"] == "acknowledged"

    resolved = client.post(f"/api/v1/alerts/{alert_id}/resolve")
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    assert resolved.json()["resolved_at"] is not None


def test_acknowledge_unknown_alert_is_404(client: TestClient) -> None:
    response = client.post(f"/api/v1/alerts/{uuid.uuid4()}/acknowledge")
    assert response.status_code == 404
