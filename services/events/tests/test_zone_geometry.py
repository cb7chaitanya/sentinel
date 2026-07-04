import pytest
from events.domain.zone import Point, Polygon
from pydantic import ValidationError


def _square(size: float = 10.0) -> Polygon:
    return Polygon(
        points=[
            Point(x=0, y=0),
            Point(x=size, y=0),
            Point(x=size, y=size),
            Point(x=0, y=size),
        ]
    )


def test_point_inside_a_square_is_contained() -> None:
    assert _square().contains(Point(x=5, y=5)) is True


def test_point_outside_a_square_is_not_contained() -> None:
    assert _square().contains(Point(x=50, y=50)) is False


def test_point_far_outside_is_not_contained() -> None:
    assert _square().contains(Point(x=-100, y=-100)) is False


def test_triangle_contains_interior_point() -> None:
    triangle = Polygon(points=[Point(x=0, y=0), Point(x=10, y=0), Point(x=5, y=10)])

    assert triangle.contains(Point(x=5, y=3)) is True
    assert triangle.contains(Point(x=1, y=9)) is False


def test_concave_polygon_excludes_points_in_the_notch() -> None:
    # A "C" / arrow-like concave shape: a 10x10 square with a notch cut
    # out of the middle of its right edge, biting in to x=5.
    concave = Polygon(
        points=[
            Point(x=0, y=0),
            Point(x=10, y=0),
            Point(x=10, y=4),
            Point(x=5, y=4),
            Point(x=5, y=6),
            Point(x=10, y=6),
            Point(x=10, y=10),
            Point(x=0, y=10),
        ]
    )

    # Inside the solid left part of the shape.
    assert concave.contains(Point(x=2, y=5)) is True
    # Inside the notch (to the right of x=5, between y=4 and y=6) -- carved out.
    assert concave.contains(Point(x=8, y=5)) is False
    # Inside the solid part above/below the notch.
    assert concave.contains(Point(x=8, y=1)) is True
    assert concave.contains(Point(x=8, y=9)) is True


def test_polygon_requires_at_least_three_points() -> None:
    with pytest.raises(ValidationError):
        Polygon(points=[Point(x=0, y=0), Point(x=1, y=1)])


def test_arbitrary_pentagon_shape() -> None:
    pentagon = Polygon(
        points=[
            Point(x=5, y=0),
            Point(x=10, y=4),
            Point(x=8, y=10),
            Point(x=2, y=10),
            Point(x=0, y=4),
        ]
    )

    assert pentagon.contains(Point(x=5, y=5)) is True
    assert pentagon.contains(Point(x=0, y=0)) is False
