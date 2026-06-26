# SPDX-License-Identifier: BSD-3-Clause
"""WGS84 polygon with bounding box, median, and SAT collision.

Port of the C++ ``HighPrecWgs84Polygon`` (``cpp/include/ndsmath/wgs84polygon.h``).
A :class:`~ndslive.math.polygon.Polygon` of :class:`~ndslive.math.wgs84.Wgs84`
vertices, defaulting to ``SIMPLE_POLYGON``, with:

* :meth:`aa_bb` — the axis-aligned bounding box,
* :meth:`median` — the centroid (with a *deliberately preserved* lon/lat swap
  quirk from the C++ reference),
* :meth:`collides_with` — Separating-Axis-Theorem collision detection.

The collision math runs on raw ``(lon, lat)`` doubles: no normalization, no
antimeridian handling.
"""

from __future__ import annotations

from .polygon import Polygon, PolygonType
from .vec2 import Vec2
from .wgs84 import Wgs84
from .wgs84_aabb import Wgs84Aabb


class Wgs84Polygon(Polygon):
    """A simple polygon of WGS84 vertices with collision and bbox helpers."""

    def __init__(
        self,
        polygon_type: PolygonType | None = None,
        vertices: list[Wgs84] | None = None,
    ) -> None:
        """Construct a WGS84 polygon.

        Defaults to ``SIMPLE_POLYGON``. Both ``polygon_type`` and ``vertices``
        are optional, mirroring the four C++ constructors:

        * ``Wgs84Polygon()`` — empty simple polygon,
        * ``Wgs84Polygon(vertices=...)`` — simple polygon with vertices,
        * ``Wgs84Polygon(polygon_type)`` — empty polygon of the given type,
        * ``Wgs84Polygon(polygon_type, vertices)`` — given type and vertices.
        """
        if polygon_type is None:
            polygon_type = PolygonType.SIMPLE_POLYGON
        super().__init__(polygon_type, vertices)

    @staticmethod
    def earth_wrapping_poly() -> Wgs84Polygon:
        """The 4-vertex sentinel polygon wrapping the whole Earth.

        Constructed from ``(-180,-90), (-180,90), (180,-90), (180,90)``. These
        coordinates pass through :class:`Wgs84` normalization, so the stored
        values are not exactly those literals. This polygon is only used as an
        identity sentinel in :meth:`collides_with` via ``==``; its exact
        normalized coordinates are not part of cross-language parity.
        """
        return Wgs84Polygon(
            vertices=[
                Wgs84(-180.0, -90.0),
                Wgs84(-180.0, 90.0),
                Wgs84(180.0, -90.0),
                Wgs84(180.0, 90.0),
            ]
        )

    def is_valid(self) -> bool:
        """Whether this is a valid polygon: at least 3 vertices."""
        return len(self._vertices) >= 3

    def __eq__(self, other: object) -> bool:
        """Order-sensitive vertex-wise equality (via ``Wgs84`` approximate ==)."""
        if not isinstance(other, Wgs84Polygon):
            return NotImplemented
        v = self._vertices
        vo = other._vertices
        if len(v) != len(vo):
            return False
        return all(v[i] == vo[i] for i in range(len(v)))

    __hash__ = None  # type: ignore[assignment]

    def aa_bb(self) -> Wgs84Aabb:
        """The axis-aligned bounding box of this polygon.

        Returns a default (empty) :class:`Wgs84Aabb` if the polygon is invalid
        (fewer than 3 vertices). The size is computed as raw coordinate
        differences (not normalized), then handed to the ``Wgs84Aabb``
        constructor, which still applies the excess-height clamp.
        """
        if not self.is_valid():
            return Wgs84Aabb()

        min_lon = min(v.longitude() for v in self._vertices)
        max_lon = max(v.longitude() for v in self._vertices)
        min_lat = min(v.latitude() for v in self._vertices)
        max_lat = max(v.latitude() for v in self._vertices)

        return Wgs84Aabb(Wgs84(min_lon, min_lat), Vec2(max_lon - min_lon, max_lat - min_lat))

    def median(self) -> Wgs84:
        """The centroid (mean longitude, mean latitude) of the polygon vertices.

        The means are accumulated as ``sum(coord / n)`` (not ``sum(coord) / n``)
        to match the C++ reference's floating-point rounding.
        """
        n = len(self._vertices)
        med_lat = 0.0
        for p in self._vertices:
            med_lat += p.latitude() / n
        med_lon = 0.0
        for p in self._vertices:
            med_lon += p.longitude() / n
        return Wgs84(med_lon, med_lat)

    def collides_with(self, other: Wgs84Polygon) -> bool:
        """Whether this polygon collides with ``other`` (Separating-Axis Theorem).

        The earth-wrapping sentinel collides with everything. Otherwise the SAT
        axis sets are taken from this polygon's edges (first test) and from
        ``other``'s edges (second test); if no separating axis is found on
        either, the polygons collide.
        """
        earth = Wgs84Polygon.earth_wrapping_poly()
        if self == earth or other == earth:
            return True
        if self._are_separate(other, self):
            return False
        # NOTE: the C++ reference passes (other, other) here — axes come from
        # `other`'s edges, projecting both `self` and `other`. Preserved exactly.
        if self._are_separate(other, other):
            return False
        return True

    @staticmethod
    def _project_on_axis(poly: Wgs84Polygon, axis: Vec2) -> Vec2:
        """Project ``poly`` onto ``axis``, returning ``Vec2(min, max)``."""
        minimum = float("inf")
        maximum = float("-inf")

        vs = poly._vertices
        n = len(vs)
        for i in range(n):
            ni = 0 if i + 1 == n else i + 1
            beg_x, beg_y = vs[i].longitude(), vs[i].latitude()
            end_x, end_y = vs[ni].longitude(), vs[ni].latitude()

            x0 = beg_x * axis.x + beg_y * axis.y
            if x0 < minimum:
                minimum = x0
            if x0 > maximum:
                maximum = x0

            x1 = x0 + (end_x - beg_x) * axis.x + (end_y - beg_y) * axis.y
            if x1 < minimum:
                minimum = x1
            if x1 > maximum:
                maximum = x1

        return Vec2(minimum, maximum)

    @staticmethod
    def _are_separate_1d(min_max1: Vec2, min_max2: Vec2) -> bool:
        """Whether two 1D intervals ``(min, max)`` are disjoint."""
        return (min_max1.x < min_max2.x and min_max1.y < min_max2.x) or (
            min_max1.x > min_max2.y and min_max1.y > min_max2.y
        )

    def _are_separate(self, other: Wgs84Polygon, ref_for_axis: Wgs84Polygon) -> bool:
        """Whether a separating axis exists among ``ref_for_axis``'s edge normals."""
        vs = ref_for_axis._vertices
        n = len(vs)
        for i in range(n):
            ni = 0 if i + 1 == n else i + 1
            dx = vs[ni].longitude() - vs[i].longitude()
            dy = vs[ni].latitude() - vs[i].latitude()
            normal = Vec2(dy, -dx)

            min_max_poly1 = self._project_on_axis(self, normal)
            min_max_poly2 = self._project_on_axis(other, normal)

            if self._are_separate_1d(min_max_poly1, min_max_poly2):
                return True
        return False
