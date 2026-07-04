"""Base schema types reused by domain-specific schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SentinelModel(BaseModel):
    """Base class for all Sentinel schemas: immutable, strict, ORM-friendly."""

    model_config = ConfigDict(from_attributes=True, frozen=True, extra="forbid")


class TimestampedModel(SentinelModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    created_at: datetime
    updated_at: datetime
