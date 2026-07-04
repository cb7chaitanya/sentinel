"""Domain value objects for warehouse zone geometry.

Zones are engine configuration, not a cross-service wire format -- the
boundary artifact this service produces is
`sentinel_common.schemas.zone.ZoneTransition` -- so `Point`/`Polygon`/`Zone`
stay local to the events service, the same way ingestion's `StreamSource`
(config) stays local while the `Frame` it produces is shared.

A zone's polygon is defined in one camera's pixel space (there's no
camera calibration/homography in this codebase yet to support real-world
coordinates), so every `Zone` names the single camera it applies to.
`warehouse_id` groups zones/cameras for multi-warehouse deployments and
keeps otherwise-identically-named zones ("Loading Dock") in different
warehouses from colliding -- state in the engine is keyed by `Zone.id`,
which must be unique across the whole deployment, not by name.
"""

import uuid

from pydantic import Field
from sentinel_common.schemas.common import SentinelModel


class Point(SentinelModel):
    x: float
    y: float


class Polygon(SentinelModel):
    """An arbitrary simple (non-self-intersecting) polygon, convex or concave."""

    points: list[Point] = Field(min_length=3)

    def contains(self, point: Point) -> bool:
        """Ray-casting point-in-polygon test (even-odd rule).

        Casts a ray from `point` in the +x direction and counts polygon
        edge crossings; an odd count means the point is inside. Works for
        any simple polygon regardless of vertex count or convexity. Points
        that fall exactly on an edge may resolve either way -- an
        acceptable ambiguity for tracked-object positions, which are
        effectively never exactly on a line.
        """
        inside = False
        vertices = self.points
        vertex_count = len(vertices)
        previous = vertex_count - 1
        for current in range(vertex_count):
            xi, yi = vertices[current].x, vertices[current].y
            xj, yj = vertices[previous].x, vertices[previous].y
            if (yi > point.y) != (yj > point.y):
                x_intersect = (xj - xi) * (point.y - yi) / (yj - yi) + xi
                if point.x < x_intersect:
                    inside = not inside
            previous = current
        return inside


class Zone(SentinelModel):
    """A named polygon zone within one camera's frame, scoped to a warehouse."""

    id: uuid.UUID
    warehouse_id: uuid.UUID
    camera_id: uuid.UUID
    name: str
    polygon: Polygon
