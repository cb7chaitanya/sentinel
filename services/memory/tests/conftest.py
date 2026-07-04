"""Shared fixtures for integration tests against a real Postgres.

These tests exercise real SQL (upserts, ordering, indexes), so they run
against an actual Postgres instance rather than mocks -- set DATABASE_URL
to point at one (see README/CI for how). Each repository write commits its
own transaction, so test isolation comes from truncating tables after each
test, not from rolling back an outer transaction.

The engine is built fresh per test (not once at module scope): asyncpg's
connection pool binds to whatever asyncio event loop is running when it's
first used, and pytest-asyncio gives each test function its own loop, so a
module-level engine would break on the second test with a
"Future attached to a different loop" error.
"""

import os
from collections.abc import AsyncIterator

import pytest
from sentinel_common.db.session import build_engine
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

TEST_DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://sentinel:sentinel@localhost:5433/sentinel_test"
)

_TABLES = ("zone_occupancy", "alerts", "events", "entities", "cameras")


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = build_engine(TEST_DATABASE_URL)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_factory() as db_session:
        yield db_session

    async with session_factory() as cleanup_session:
        for table in _TABLES:
            await cleanup_session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        await cleanup_session.commit()

    await engine.dispose()
