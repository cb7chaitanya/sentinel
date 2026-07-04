"""SQLAlchemy ORM models backing the memory service's persistence layer."""

import uuid
from datetime import datetime

from sentinel_common.db.base import Base, TimestampMixin
from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Camera(TimestampMixin, Base):
    __tablename__ = "cameras"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    rtsp_url: Mapped[str] = mapped_column(String(2048))
    zone: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)


class Entity(TimestampMixin, Base):
    """A tracked object: one row per (camera_id, track_id) ever observed.

    `camera_id`/`warehouse_id` are plain indexed columns, not foreign keys:
    cameras and warehouses aren't rows in this database (they're static
    ingestion/events configuration -- see services/ingestion's
    `StreamSource` and services/events' `Zone`), so there's nothing to
    reference. Unrelated to `cameras` above, which is a separate,
    currently-unused camera-configuration table.
    """

    __tablename__ = "entities"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(index=True)
    camera_id: Mapped[uuid.UUID] = mapped_column(index=True)
    track_id: Mapped[int]
    entity_type: Mapped[str] = mapped_column(String(32))
    label: Mapped[str] = mapped_column(String(255))

    bbox_x_min: Mapped[float]
    bbox_y_min: Mapped[float]
    bbox_x_max: Mapped[float]
    bbox_y_max: Mapped[float]
    velocity_vx: Mapped[float | None] = mapped_column(nullable=True)
    velocity_vy: Mapped[float | None] = mapped_column(nullable=True)

    first_seen_at: Mapped[datetime]
    last_seen_at: Mapped[datetime] = mapped_column(index=True)

    zone_occupancy: Mapped[list["ZoneOccupancy"]] = relationship(back_populates="entity")

    __table_args__ = (
        UniqueConstraint("camera_id", "track_id"),
        Index("ix_entities_warehouse_last_seen", "warehouse_id", "last_seen_at"),
    )


class ZoneOccupancy(TimestampMixin, Base):
    """One continuous stay in a zone. `exited_at IS NULL` while still inside."""

    __tablename__ = "zone_occupancy"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(index=True)
    zone_id: Mapped[uuid.UUID] = mapped_column(index=True)
    zone_name: Mapped[str] = mapped_column(String(255))
    entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id"), index=True)
    entered_at: Mapped[datetime]
    exited_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)

    entity: Mapped["Entity"] = relationship(back_populates="zone_occupancy")

    __table_args__ = (
        Index("ix_zone_occupancy_warehouse_zone_exited", "warehouse_id", "zone_id", "exited_at"),
    )


class Event(TimestampMixin, Base):
    """Append-only activity log. See sentinel_common.schemas.event.EventBase.

    `camera_id` is not a foreign key to `cameras` (see `Entity` above for
    why): events reference whatever camera the tracking pipeline reported,
    independent of the separate camera-configuration table.
    """

    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    warehouse_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    camera_id: Mapped[uuid.UUID] = mapped_column(index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(index=True)
    summary: Mapped[str] = mapped_column(String(1024))

    track_id: Mapped[int | None] = mapped_column(nullable=True)
    zone_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    zone_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dwell_time_seconds: Mapped[float | None] = mapped_column(nullable=True)
    related_track_id: Mapped[int | None] = mapped_column(nullable=True)
    related_label: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Alert(TimestampMixin, Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(index=True)
    camera_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    event_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    severity: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="open")
    summary: Mapped[str] = mapped_column(String(1024))
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (Index("ix_alerts_warehouse_status", "warehouse_id", "status"),)
