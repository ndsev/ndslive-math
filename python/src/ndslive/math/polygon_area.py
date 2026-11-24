# SPDX-License-Identifier: BSD-3-Clause
"""Closed planar polygon/rectangle intersection, with open hole interiors.

Coordinates remain raw; geographic callers must unwrap all rings and queries
into the same plane. Validate a polygon once before classifying rectangles.
"""

import math
from collections.abc import Sequence
from enum import IntEnum

from .vec2 import Vec2


class PolygonAreaRelation(IntEnum):
    """Relation of a closed rectangle to a valid polygon area."""

    OUTSIDE = 0
    INSIDE = 1
    BOUNDARY = 2


def _size(ring: Sequence[Vec2]) -> int:
    """Ignore one conventional repeated closing vertex."""
    return len(ring) - (len(ring) > 1 and ring[0] == ring[-1])


def _cross(a: Vec2, b: Vec2, c: Vec2) -> float:
    """Orientation with an exact expansion fallback for cancellation.

    Only the sign is significant. Error-free differences/products retain small
    NDS-coordinate turns without introducing a geometric tolerance.
    """
    left, right = (b.x - a.x) * (c.y - a.y), (b.y - a.y) * (c.x - a.x)
    determinant = left - right
    if abs(determinant) > (abs(left) + abs(right)) * 8 * math.ulp(1.0):
        return determinant
    expansion: list[float] = []
    for x, y, sign in (
        (_difference(b.x, a.x), _difference(c.y, a.y), 1),
        (_difference(b.y, a.y), _difference(c.x, a.x), -1),
    ):
        for u in x:
            for v in y:
                for term in _product(u, v):
                    expansion = _grow(expansion, sign * term)
    return expansion[-1] if expansion else 0.0


def _difference(a: float, b: float) -> tuple[float, float]:
    """Return the exact difference as low/high floating-point components."""
    high = a - b
    virtual_b = a - high
    return (a - (high + virtual_b)) + (virtual_b - b), high


def _product(a: float, b: float) -> tuple[float, float]:
    """Dekker product, without requiring a platform fused multiply-add."""
    high = a * b
    sa, sb = 134217729.0 * a, 134217729.0 * b
    ah, bh = sa - (sa - a), sb - (sb - b)
    al, bl = a - ah, b - bh
    return ((ah * bh - high) + ah * bl + al * bh) + al * bl, high


def _grow(expansion: list[float], value: float) -> list[float]:
    """Add one component to a nonoverlapping expansion without losing bits."""
    result = []
    for term in expansion:
        total = value + term
        virtual = total - value
        low = (value - (total - virtual)) + (term - virtual)
        if low:
            result.append(low)
        value = total
    if value:
        result.append(value)
    return result


def _on(p: Vec2, a: Vec2, b: Vec2) -> bool:
    """Closed segment membership, including endpoints."""
    return (
        _cross(a, b, p) == 0
        and min(a.x, b.x) <= p.x <= max(a.x, b.x)
        and min(a.y, b.y) <= p.y <= max(a.y, b.y)
    )


def _intersects(a: Vec2, b: Vec2, c: Vec2, d: Vec2) -> bool:
    """Closed segment intersection, including collinear contact."""
    ab_c, ab_d, cd_a, cd_b = _cross(a, b, c), _cross(a, b, d), _cross(c, d, a), _cross(c, d, b)
    return (
        (((ab_c < 0 < ab_d) or (ab_d < 0 < ab_c)) and ((cd_a < 0 < cd_b) or (cd_b < 0 < cd_a)))
        or _on(a, c, d)
        or _on(b, c, d)
        or _on(c, a, b)
        or _on(d, a, b)
    )


def _contains(ring: Sequence[Vec2], p: Vec2) -> bool:
    """Even/odd containment, with ring boundaries included."""
    inside = False
    n = _size(ring)
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        if _on(p, a, b):
            return True
        if (a.y > p.y) != (b.y > p.y) and (_cross(a, b, p) > 0) == (b.y > a.y):
            inside = not inside
    return inside


def _rings_intersect(a: Sequence[Vec2], b: Sequence[Vec2]) -> bool:
    """Detect contact between ring boundaries."""
    na, nb = _size(a), _size(b)
    return any(
        _intersects(a[i], a[(i + 1) % na], b[j], b[(j + 1) % nb])
        for i in range(na)
        for j in range(nb)
    )


def _valid_ring(ring: Sequence[Vec2]) -> bool:
    """Require a finite nondegenerate simple ring, preserving winding."""
    n, noncollinear = _size(ring), False
    if n < 3:
        return False
    for i in range(n):
        a, b, previous = ring[i], ring[(i + 1) % n], ring[(i + n - 1) % n]
        if not math.isfinite(a.x) or not math.isfinite(a.y) or a == b:
            return False
        turn = _cross(previous, a, b)
        if not math.isfinite(turn) or (turn == 0 and not _on(a, previous, b)):
            return False
        # Simplicity plus a non-collinear turn proves positive area magnitude;
        # summing absolute-coordinate shoelace products can cancel to zero.
        noncollinear |= turn != 0
        for j in range(i + 1, n):
            if (
                j != i + 1
                and not (i == 0 and j == n - 1)
                and _intersects(a, b, ring[j], ring[(j + 1) % n])
            ):
                return False
    return noncollinear


def valid_polygon_area(exterior: Sequence[Vec2], holes: Sequence[Sequence[Vec2]] = ()) -> bool:
    """Validate a simple exterior and disjoint strictly interior holes."""
    if not _valid_ring(exterior):
        return False
    for i, hole in enumerate(holes):
        if (
            not _valid_ring(hole)
            or not _contains(exterior, hole[0])
            or _rings_intersect(exterior, hole)
        ):
            return False
        for other in holes[:i]:
            if (
                _rings_intersect(hole, other)
                or _contains(hole, other[0])
                or _contains(other, hole[0])
            ):
                return False
    return True


def polygon_areas_intersect(
    a: Sequence[Vec2],
    a_holes: Sequence[Sequence[Vec2]],
    b: Sequence[Vec2],
    b_holes: Sequence[Sequence[Vec2]],
) -> bool:
    """Intersect prevalidated areas in one plane, including all ring boundaries."""
    if not a or not b:
        return False
    if any(_rings_intersect(left, right) for left in (a, *a_holes) for right in (b, *b_holes)):
        return True
    return (_contains(b, a[0]) and not any(_contains(hole, a[0]) for hole in b_holes)) or (
        _contains(a, b[0]) and not any(_contains(hole, b[0]) for hole in a_holes)
    )


def classify_polygon_rectangle(
    exterior: Sequence[Vec2], holes: Sequence[Sequence[Vec2]], minimum: Vec2, maximum: Vec2
) -> PolygonAreaRelation:
    """Classify a closed rectangle against prevalidated rings; all boundary contact counts.

    An invalid/nonfinite rectangle or an empty exterior returns OUTSIDE. This hot
    query does not repeat polygon topology validation.
    """
    if (
        len(exterior) < 3
        or not all(math.isfinite(v) for v in (minimum.x, minimum.y, maximum.x, maximum.y))
        or minimum.x > maximum.x
        or minimum.y > maximum.y
    ):
        return PolygonAreaRelation.OUTSIDE
    rectangle = [minimum, Vec2(maximum.x, minimum.y), maximum, Vec2(minimum.x, maximum.y)]
    for ring in (exterior, *holes):
        if any(
            minimum.x <= p.x <= maximum.x and minimum.y <= p.y <= maximum.y for p in ring
        ) or _rings_intersect(ring, rectangle):
            return PolygonAreaRelation.BOUNDARY
    centre = Vec2((minimum.x + maximum.x) * 0.5, (minimum.y + maximum.y) * 0.5)
    if not _contains(exterior, centre) or any(_contains(hole, centre) for hole in holes):
        return PolygonAreaRelation.OUTSIDE
    return PolygonAreaRelation.INSIDE
