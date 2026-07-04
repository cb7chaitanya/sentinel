"""Common exception hierarchy shared across Sentinel services.

Services should raise these (or subclasses) instead of ad-hoc exceptions so
that a single set of FastAPI exception handlers can translate them into
consistent HTTP responses.
"""


class SentinelError(Exception):
    """Base class for all Sentinel domain errors."""


class NotFoundError(SentinelError):
    """Raised when a requested resource does not exist."""


class ValidationError(SentinelError):
    """Raised when input fails domain-level validation."""


class DependencyUnavailableError(SentinelError):
    """Raised when an upstream service or resource cannot be reached."""
