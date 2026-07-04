"""Lightweight dependency-injection helpers shared across services.

Sentinel does not use a heavyweight DI framework. Instead, each service
composes small, typed provider functions and wires them into endpoints via
FastAPI's native `Depends()`. This module supplies the few generic
primitives that every service's `core/di.py` builds on.
"""

from collections.abc import Callable, Generator
from functools import lru_cache
from typing import TypeVar

T = TypeVar("T")


def singleton(factory: Callable[[], T]) -> Callable[[], T]:
    """Wrap a zero-arg factory so it is constructed once per process.

    Use for stateless or expensive-to-build dependencies (settings, model
    handles, HTTP clients) that should be shared across requests.
    """
    return lru_cache(maxsize=1)(factory)


def scoped(factory: Callable[[], Generator[T, None, None]]) -> Callable[[], Generator[T, None, None]]:
    """Pass-through marker for request-scoped generator dependencies.

    Kept as an explicit primitive (rather than using bare generator
    functions everywhere) so provider intent is documented at the call
    site, e.g. `get_db_session = scoped(_build_db_session)`.
    """
    return factory
