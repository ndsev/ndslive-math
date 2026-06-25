# SPDX-License-Identifier: BSD-3-Clause
"""A plain 2D vector that is *not* WGS84-normalized.

The geometry layer (``Wgs84Aabb`` in particular) needs a raw ``(dx, dy)``
extent that can legitimately exceed ``360`` / ``180`` degrees or be negative —
unlike :class:`~ndslive.math.wgs84.Wgs84`, whose constructor wraps longitude and
clamps latitude. Reusing ``Wgs84`` for a size/extent would silently corrupt
those values via normalization, so this small struct is used instead.

It mirrors the role of ``glm::dvec2`` (used as ``Wgs84<T>::vec2_t``) in the C++
reference (``cpp/include/ndsmath/wgs84aabb.h``).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass


@dataclass
class Vec2:
    """A raw, un-normalized 2D vector ``(x, y)``.

    ``x`` is the longitude/horizontal component, ``y`` the latitude/vertical
    component. Supports component-wise ``+`` / ``-`` / ``*`` (with another
    :class:`Vec2`) and scalar multiplication.
    """

    x: float = 0.0
    y: float = 0.0

    def __add__(self, other: Vec2) -> Vec2:
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vec2) -> Vec2:
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vec2:
        return Vec2(self.x * scalar, self.y * scalar)

    __rmul__ = __mul__

    def abs(self) -> Vec2:
        """Return the component-wise absolute value."""
        return Vec2(abs(self.x), abs(self.y))

    def __iter__(self) -> Iterator[float]:
        yield self.x
        yield self.y

    def __str__(self) -> str:
        return f"Vec2(x={self.x}, y={self.y})"
