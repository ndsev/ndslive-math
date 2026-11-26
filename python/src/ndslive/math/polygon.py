# SPDX-License-Identifier: BSD-3-Clause
"""Generic polygon container with orientation, mirroring the C++ ``Polygon``.

Port of ``cpp/include/ndsmath/polygon.h``. The C++ class is a template over a
vertex container; here it is specialized directly to a list of
:class:`~ndslive.math.wgs84.Wgs84` vertices. Orientation is computed on the raw
``(lon, lat)`` plane (no WGS84 normalization, no antimeridian handling).
"""

from __future__ import annotations

import math
import sys
from enum import IntEnum
from fractions import Fraction

from .wgs84 import Wgs84


class Orientation(IntEnum):
    """Winding order of a polygon. Integer values match the C++ enum."""

    CLOCKWISE = -1
    INVALID_ORIENTATION = 0
    COUNTERCLOCKWISE = 1


class PolygonType(IntEnum):
    """Polygon topology. Integer values match the C++ enum."""

    #: A simple polygon with an arbitrary number of vertices and no holes; the
    #: last vertex connects back to the first.
    SIMPLE_POLYGON = 0
    #: A triangle strip.
    TRIANGLE_STRIP = 1
    #: A triangle fan.
    TRIANGLE_FAN = 2
    #: A set of independent triangles; three consecutive vertices form one.
    TRIANGLE_LIST = 3
    #: Illegal polygon type, used to signal failure.
    UNKNOWN = 4


class Polygon:
    """A set of vertices with a topology type and orientation query.

    Mirrors the C++ ``Polygon<Vector>`` template. The base
    :meth:`is_valid` requires at least one vertex; subclasses (e.g.
    :class:`~ndslive.math.wgs84_polygon.Wgs84Polygon`) may override it.
    """

    def __init__(
        self,
        polygon_type: PolygonType = PolygonType.UNKNOWN,
        vertices: list[Wgs84] | None = None,
    ) -> None:
        """Construct a polygon.

        Args:
            polygon_type: The polygon topology. Defaults to ``UNKNOWN``.
            vertices: Optional initial list (shallow-copied; Wgs84 objects remain shared).
        """
        self._polygon_type = polygon_type
        self._vertices: list[Wgs84] = list(vertices) if vertices is not None else []

    def add_vertex(self, position: Wgs84) -> None:
        """Append a single vertex."""
        self._vertices.append(position)

    def add_vertices(self, vertices: list[Wgs84]) -> None:
        """Append a list of vertices, in order."""
        self._vertices.extend(vertices)

    def __getitem__(self, index: int) -> Wgs84:
        """Read a vertex using Python list indexing, including negative indices and IndexError."""
        return self._vertices[index]

    def __setitem__(self, index: int, value: Wgs84) -> None:
        self._vertices[index] = value

    def __len__(self) -> int:
        return len(self._vertices)

    def type(self) -> PolygonType:
        """Get the polygon type."""
        return self._polygon_type

    def set_type(self, polygon_type: PolygonType) -> None:
        """Set the polygon type."""
        self._polygon_type = polygon_type

    def is_valid(self) -> bool:
        """Whether this is a valid polygon.

        Base implementation: at least one vertex. Overridden by
        :class:`~ndslive.math.wgs84_polygon.Wgs84Polygon` to require >= 3.
        """
        return len(self._vertices) > 0

    def vertices(self) -> list[Wgs84]:
        """Get the (mutable) list of vertices."""
        return self._vertices

    def orientation(self) -> Orientation:
        """Compute the winding order via the signed shoelace formula.

        Only works for ``SIMPLE_POLYGON`` and a single-triangle
        ``TRIANGLE_LIST`` (exactly 3 vertices). All other types return
        ``INVALID_ORIENTATION`` without computing area. Collinear vertices
        (zero area) also return ``INVALID_ORIENTATION``.

        Uses raw ``(lon, lat)`` doubles; no normalization.
        """
        if self._polygon_type != PolygonType.SIMPLE_POLYGON and not (
            self._polygon_type == PolygonType.TRIANGLE_LIST and len(self._vertices) == 3
        ):
            return Orientation.INVALID_ORIENTATION

        n = len(self._vertices)
        if n < 3:
            return Orientation.INVALID_ORIENTATION

        origin_x = self._vertices[0].x
        origin_y = self._vertices[0].y
        area = magnitude = 0.0
        for i in range(1, n - 1):
            a, b = self._vertices[i], self._vertices[i + 1]
            left = (a.x - origin_x) * (b.y - origin_y)
            right = (a.y - origin_y) * (b.x - origin_x)
            area += left - right
            magnitude += abs(left) + abs(right)

        # Bound rounding in the products and n additions. Never treat uncertainty as zero.
        bound = 4 * (n + 4) * sys.float_info.epsilon * (magnitude + sys.float_info.min)
        if abs(area) > bound:
            return Orientation.COUNTERCLOCKWISE if area > 0 else Orientation.CLOCKWISE
        if not all(math.isfinite(v.x) and math.isfinite(v.y) for v in self._vertices):
            return Orientation.INVALID_ORIENTATION
        points = [(Fraction(v.x), Fraction(v.y)) for v in self._vertices]
        exact = sum(points[i - 1][0] * y - points[i - 1][1] * x for i, (x, y) in enumerate(points))
        return Orientation((exact > 0) - (exact < 0))
