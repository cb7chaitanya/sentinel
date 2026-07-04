"""Schema for a single captured camera frame.

This is the boundary artifact produced by the ingestion service and handed
to any downstream consumer (e.g. vision). It carries only pixel data and
capture metadata -- never inference results -- so producing it never
requires knowing anything about AI.
"""

import uuid
from datetime import datetime

from pydantic import Field

from sentinel_common.schemas.common import SentinelModel


class Frame(SentinelModel):
    camera_id: uuid.UUID
    sequence: int = Field(ge=0)
    captured_at: datetime
    data: bytes
    width: int = Field(gt=0)
    height: int = Field(gt=0)
