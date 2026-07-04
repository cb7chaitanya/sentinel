"""Schemas describing a monitored warehouse camera / RTSP source."""

from pydantic import AnyUrl

from sentinel_common.schemas.common import SentinelModel, TimestampedModel


class CameraBase(SentinelModel):
    name: str
    rtsp_url: AnyUrl
    zone: str | None = None
    is_active: bool = True


class CameraCreate(CameraBase):
    pass


class CameraRead(CameraBase, TimestampedModel):
    pass
