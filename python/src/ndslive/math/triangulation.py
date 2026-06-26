# SPDX-License-Identifier: BSD-3-Clause
"""Ear-clipping polygon triangulation.

Port of the C++ ``PolygonTriangulation`` (``cpp/include/ndsmath/
polygontriangulation.h`` and ``.cpp``). The C++ implementation uses a
pointer-linked ring of partition vertices; this port uses an index-linked
``list`` of :class:`_PartitionVertex` (``prev`` / ``next`` integer indices)
to avoid manual memory management while reproducing the same traversal.

.. note::

    The *set* of output triangles is deterministic, but the ordering of
    triangles and the rotation of each triangle's three vertices are
    implementation-specific (driven by the "most extruded ear" tie-break and
    floating-point ``angle`` comparisons). Triangulation output is therefore
    **not** part of the cross-language parity vectors; tests assert structure
    (type and vertex count) only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .polygon import PolygonType
from .wgs84 import Wgs84
from .wgs84_polygon import Wgs84Polygon


@dataclass
class _PartitionVertex:
    """A node in the ear-clipping ring (index-linked replacement for pointers)."""

    is_active: bool
    is_convex: bool
    is_ear: bool
    p: Wgs84
    angle: float
    previous: int
    next: int


class PolygonTriangulation:
    """Triangulates simple polygons by ear clipping (O(n^2))."""

    def triangulate_by_ear_clipping(self, polygon: Wgs84Polygon) -> Wgs84Polygon:
        """Triangulate a CCW simple polygon into a ``TRIANGLE_LIST``.

        Args:
            polygon: A ``SIMPLE_POLYGON`` with at least 3 vertices, in
                counter-clockwise order.

        Returns:
            A :class:`Wgs84Polygon` of type ``TRIANGLE_LIST`` on success
            (``3 * (n - 2)`` vertices), or a polygon of type ``UNKNOWN`` on
            failure (wrong type, too few vertices, or no ear found).
        """
        result = Wgs84Polygon(PolygonType.TRIANGLE_LIST)

        if polygon.type() != PolygonType.SIMPLE_POLYGON or len(polygon.vertices()) < 3:
            return Wgs84Polygon(PolygonType.UNKNOWN)

        num_vertices = len(polygon.vertices())

        # Nothing to do for a single triangle.
        if num_vertices == 3:
            result.add_vertices(list(polygon.vertices()))
            return result

        vertices: list[_PartitionVertex] = []
        for i in range(num_vertices):
            vertices.append(
                _PartitionVertex(
                    is_active=True,
                    is_convex=False,
                    is_ear=False,
                    p=polygon[i],
                    angle=0.0,
                    next=(0 if i == num_vertices - 1 else i + 1),
                    previous=(num_vertices - 1 if i == 0 else i - 1),
                )
            )

        for i in range(num_vertices):
            self._update_vertex(i, vertices, num_vertices)

        ear = -1
        for i in range(num_vertices - 3):
            ear_found = False

            # Find the most extruded ear (largest angle; first wins ties).
            for j in range(num_vertices):
                if not vertices[j].is_active or not vertices[j].is_ear:
                    continue
                if not ear_found:
                    ear_found = True
                    ear = j
                elif vertices[j].angle > vertices[ear].angle:
                    ear = j

            if not ear_found:
                return Wgs84Polygon(PolygonType.UNKNOWN)

            ear_v = vertices[ear]
            result.add_vertex(vertices[ear_v.previous].p)
            result.add_vertex(ear_v.p)
            result.add_vertex(vertices[ear_v.next].p)

            ear_v.is_active = False
            vertices[ear_v.previous].next = ear_v.next
            vertices[ear_v.next].previous = ear_v.previous

            if i == num_vertices - 4:
                break

            self._update_vertex(ear_v.previous, vertices, num_vertices)
            self._update_vertex(ear_v.next, vertices, num_vertices)

        for i in range(num_vertices):
            if vertices[i].is_active:
                result.add_vertex(vertices[vertices[i].previous].p)
                result.add_vertex(vertices[i].p)
                result.add_vertex(vertices[vertices[i].next].p)
                break

        return result

    @staticmethod
    def _normalize(p: Wgs84) -> Wgs84:
        """Vector-normalize ``p``; ``(0, 0)`` if it has zero length.

        Mirrors the C++ ``normalize``: the unit vector is wrapped back into a
        :class:`Wgs84` (which re-normalizes as a coordinate). Odd, but part of
        the reference behavior.
        """
        n = math.sqrt(p.x * p.x + p.y * p.y)
        if n != 0.0:
            return Wgs84(p.x / n, p.y / n)
        return Wgs84(0.0, 0.0)

    @staticmethod
    def _is_convex(p1: Wgs84, p2: Wgs84, p3: Wgs84) -> bool:
        """Whether the turn ``p1 -> p2 -> p3`` is convex (positive cross product)."""
        return (p3.y - p1.y) * (p2.x - p1.x) - (p3.x - p1.x) * (p2.y - p1.y) > 0.0

    def _is_inside(self, p1: Wgs84, p2: Wgs84, p3: Wgs84, p: Wgs84) -> bool:
        """Whether point ``p`` lies inside triangle ``(p1, p2, p3)``."""
        return (
            not self._is_convex(p1, p, p2)
            and not self._is_convex(p2, p, p3)
            and not self._is_convex(p3, p, p1)
        )

    def _update_vertex(
        self, v_idx: int, vertices: list[_PartitionVertex], num_vertices: int
    ) -> None:
        """Recompute convexity, ear status, and angle of vertex ``v_idx``."""
        v = vertices[v_idx]
        v1 = vertices[v.previous]
        v3 = vertices[v.next]
        v.is_convex = self._is_convex(v1.p, v.p, v3.p)

        vec1 = self._normalize(v1.p - v.p)
        vec3 = self._normalize(v3.p - v.p)

        v.angle = vec1.x * vec3.x + vec1.y * vec3.y

        if v.is_convex:
            v.is_ear = True
            for i in range(num_vertices):
                if vertices[i].p.x == v.p.x and vertices[i].p.y == v.p.y:
                    continue
                if vertices[i].p.x == v1.p.x and vertices[i].p.y == v1.p.y:
                    continue
                if vertices[i].p.x == v3.p.x and vertices[i].p.y == v3.p.y:
                    continue
                if self._is_inside(v1.p, v.p, v3.p, vertices[i].p):
                    v.is_ear = False
                    break
        else:
            v.is_ear = False
