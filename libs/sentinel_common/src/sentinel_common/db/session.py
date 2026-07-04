"""Async SQLAlchemy engine/session factory shared by every service.

Services that talk to Postgres call `build_session_factory(database_url)`
once at startup (see `core/di.py`) and expose a `get_db_session` FastAPI
dependency built on top of `iter_session`.
"""

from collections.abc import AsyncGenerator, Callable

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def build_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    return create_async_engine(database_url, echo=echo, pool_pre_ping=True)


def build_session_factory(database_url: str, *, echo: bool = False) -> async_sessionmaker[AsyncSession]:
    engine = build_engine(database_url, echo=echo)
    return async_sessionmaker(bind=engine, expire_on_commit=False)


def make_session_dependency(
    session_factory: async_sessionmaker[AsyncSession],
) -> Callable[[], AsyncGenerator[AsyncSession, None]]:
    """Build a FastAPI dependency that yields a request-scoped session."""

    async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    return get_db_session
