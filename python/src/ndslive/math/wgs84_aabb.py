# SPDX-License-Identifier: BSD-3-Clause
"""WGS84 axis-aligned bounding box.

Port of the C++ ``Wgs84AABB<T>`` (``cpp/include/ndsmath/wgs84aabb.h``),
specialized to ``double``. The box is stored as a south-west corner
(:class:`~ndslive.math.wgs84.Wgs84`) plus a raw :class:`~ndslive.math.vec2.Vec2`
size (a ``(dx, dy)`` extent that is *not* normalized).

The geometry layer deliberately uses the power-of-two NDS deltas
(``Wgs84.LON_NDS_DELTA_POW2`` etc.) for antimeridian handling and tile-from-index
construction, as the C++ reference does. Constructor normalization still follows
this port's Wgs84, so the shared constants alone do not ensure parity.
"""

from __future__ import annotations

import math

from .morton import MortonCode
from .tileid import PackedTileId
from .vec2 import Vec2
from .wgs84 import Wgs84


class Wgs84Aabb:
    """A WGS84 axis-aligned bounding box defined by a SW corner and a size."""

    def __init__(self, sw: Wgs84 | None = None, size: Vec2 | None = None) -> None:
        """Construct an AABB from a south-west corner and a size.

        Args:
            sw: South-west corner. Defaults to ``Wgs84(0, 0)``.
            size: Raw ``(dx, dy)`` extent. Defaults to ``Vec2(0, 0)``.

        After storing, if the box is :meth:`valid`, the height is clamped so the
        top never exceeds +90 degrees (``excessHeight`` correction). An invalid
        box stores ``size`` unmodified. Both arguments are retained by reference;
        the height clamp mutates the supplied size, and later caller edits affect the box.
        """
        self._sw: Wgs84 = sw if sw is not None else Wgs84(0.0, 0.0)
        self._size: Vec2 = size if size is not None else Vec2(0.0, 0.0)

        if not self.valid():
            return

        excess_height = 90.0 - self._sw.latitude() - self._size.y
        if excess_height < 0:
            self._size.y += excess_height

    @classmethod
    def from_tile(cls, tile_id: PackedTileId) -> Wgs84Aabb:
        """Construct an AABB from a tile (via ``from_morton_code``).

        Like the C++ ``Wgs84AABB(PackedTileId)`` constructor, this wraps the SW/NE
        NDS corners into :class:`~ndslive.math.morton.MortonCode` and converts
        them to WGS84. Both axes use the same scale: ``360 / 2^32 = 180 / 2^31``.
        At the world edge, the NE corner can wrap to the opposite side. Taking
        the absolute corner difference then produces an almost-world-wide box
        instead of the tile's width.

        Args:
            tile_id: The tile whose extent the AABB should cover.

        Returns:
            A new :class:`Wgs84Aabb`.
        """
        sw_x, sw_y = tile_id.south_west_corner()
        ne_x, ne_y = tile_id.north_east_corner()

        sw_corner = Wgs84.from_morton_code(MortonCode.from_nds_coordinates(sw_x, sw_y))
        ne_corner = Wgs84.from_morton_code(MortonCode.from_nds_coordinates(ne_x, ne_y))

        size = Vec2(sw_corner.x - ne_corner.x, sw_corner.y - ne_corner.y).abs()
        return cls(sw_corner, size)

    @classmethod
    def from_center_and_tile_limit(cls, center: Wgs84, soft_limit: int, level: int) -> Wgs84Aabb:
        """Construct an AABB from a center, a soft tile-count limit, and a level.

        Args:
            center: The center coordinate of the box.
            soft_limit: Nonnegative target area in tile footprints, not a cap
                on enumerated tiles.
            level: NDS tile level (0..15).

        Returns:
            A new :class:`Wgs84Aabb`; pole clamping can move its final center.
        """
        target_aspect_ratio = 0.7  # height/width is this factor squared
        tile_width = 180.0 / float(1 << level)
        target_size = math.sqrt(soft_limit) * tile_width
        target_size_vec = Vec2(target_size / target_aspect_ratio, target_size * target_aspect_ratio)
        half = target_size_vec * 0.5
        new_sw = Wgs84(center.x - half.x, center.y - half.y)
        return cls(new_sw, target_size_vec)

    def valid(self) -> bool:
        """Whether the box size is within reasonable bounds.

        ``0 <= size.x <= 360`` and ``0 <= size.y <= 180``.
        """
        return (
            self._size.x >= 0
            and self._size.y >= 0
            and self._size.x <= 360.0
            and self._size.y <= 180.0
        )

    def sw(self) -> Wgs84:
        """The south-west corner. Returns the stored point, so changes to it affect the box."""
        return self._sw

    def ne(self) -> Wgs84:
        """The north-east corner (``sw + size``, re-normalized)."""
        return Wgs84(self._sw.x + self._size.x, self._sw.y + self._size.y)

    def nw(self) -> Wgs84:
        """The north-west corner."""
        return Wgs84(self._sw.x, self._sw.y + self._size.y)

    def se(self) -> Wgs84:
        """The south-east corner."""
        return Wgs84(self._sw.x + self._size.x, self._sw.y)

    def vertices(self) -> list[Wgs84]:
        """All four corners, CCW from SW: ``[sw, se, ne, nw]``."""
        return [self.sw(), self.se(), self.ne(), self.nw()]

    def size(self) -> Vec2:
        """The raw ``(dx, dy)`` size of the box. Returns the stored, mutable vector."""
        return self._size

    def contains_anti_meridian(self) -> bool:
        """Whether the horizontal extent crosses the anti-meridian (+/-180)."""
        return self._sw.longitude() + self._size.x > Wgs84.LON_MAX + Wgs84.LON_NDS_DELTA_POW2

    def center(self) -> Wgs84:
        """The center coordinate (``sw + size * 0.5``, re-normalized)."""
        half = self._size * 0.5
        return Wgs84(self._sw.x + half.x, self._sw.y + half.y)

    def split_over_anti_meridian(self) -> tuple[Wgs84Aabb, Wgs84Aabb] | None:
        """Split a box crossing the anti-meridian into a left and right half.

        Only meaningful when :meth:`contains_anti_meridian` is true.

        Returns:
            A ``(left, right)`` tuple of normalized boxes, or ``None`` if the
            box does not actually extend past ``LON_MAX``.
        """
        width_after_am = self._sw.longitude() + self._size.x - Wgs84.LON_MAX
        if width_after_am > 0:
            width_before_am = self._size.x - width_after_am
            left = Wgs84Aabb(self._sw, Vec2(width_before_am, self._size.y))
            right = Wgs84Aabb(
                Wgs84(Wgs84.LON_MIN, self._sw.latitude()),
                Vec2(width_after_am, self._size.y),
            )
            return (left, right)
        return None

    def avg_mercator_stretch(self) -> float:
        """The Mercator-projection vertical stretch factor, averaged over the box.

        Transcendental; not part of the cross-language parity vectors (asserted
        only for finiteness in unit tests). Requires nonzero height and finite
        projected latitudes.
        """
        lat_top = math.radians(self._sw.latitude() + self._size.y)
        lat_bottom = math.radians(self._sw.latitude())

        def rad_to_mercator_lat(wgs84_lat: float) -> float:
            return math.atanh(math.sin(wgs84_lat - math.pi / 2.0))

        return (rad_to_mercator_lat(lat_top) - rad_to_mercator_lat(lat_bottom)) / math.radians(
            self._size.y
        )

    def num_tile_ids(self, lv: int) -> int:
        """Approximate number of tiles at level ``lv`` contained in this box.

        Mirrors the C++ ``numTileIds``: ``tileWidth = 180 / float(2^lv)`` and a
        component-wise ``ceil`` of ``size / tileWidth``. Invalid extents may
        yield a negative count; C++ clamps nonpositive counts to zero.
        """
        tile_width = 180.0 / float(1 << lv)
        tiles_per_dim_x = math.ceil(self._size.x / tile_width)
        tiles_per_dim_y = math.ceil(self._size.y / tile_width)
        return int(tiles_per_dim_x * tiles_per_dim_y)

    def tile_level(self, min_num_tiles: int = 8) -> int:
        """First level (0..15) whose tile count is at least ``min_num_tiles``.

        Returns 15 if no level in ``0..15`` reaches the threshold.
        """
        for result_tile_level in range(0, 16):
            if self.num_tile_ids(result_tile_level) >= min_num_tiles:
                return result_tile_level
        return 15

    def contains(self, point: Wgs84) -> bool:
        """Whether ``point`` lies within the box (inclusive on all edges).
        Split anti-meridian boxes first; longitude is not unwrapped here."""
        return (
            point.longitude() >= self._sw.longitude()
            and point.longitude() <= self._sw.longitude() + self._size.x
            and point.latitude() >= self._sw.latitude()
            and point.latitude() <= self._sw.latitude() + self._size.y
        )

    def intersects(self, other: Wgs84Aabb) -> bool:
        """Axis-aligned interval-overlap test against another box.

        This is the fixed test: a pure interval overlap on longitude and
        latitude. Edge-touching counts as intersecting; it correctly detects
        cross-shaped overlaps and never recurses on disjoint boxes.
        Split anti-meridian boxes before comparing; longitude is not unwrapped here.
        """
        a_max_x = self._sw.longitude() + self._size.x
        a_max_y = self._sw.latitude() + self._size.y
        b_max_x = other.sw().longitude() + other.size().x
        b_max_y = other.sw().latitude() + other.size().y
        return (
            self._sw.longitude() <= b_max_x
            and a_max_x >= other.sw().longitude()
            and self._sw.latitude() <= b_max_y
            and a_max_y >= other.sw().latitude()
        )
