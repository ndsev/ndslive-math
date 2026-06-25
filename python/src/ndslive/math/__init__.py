# SPDX-License-Identifier: BSD-3-Clause
"""ndslive.math — coordinate math, tile IDs, and Morton codes for NDS.Live.

``ndslive.math`` is the small set of geometry primitives shared by every
NDS.Live Python package: WGS84 ↔ NDS coordinate conversion, packed tile
IDs, Morton (Z-order) encoding, and bounding boxes in NDS space.

Quick examples
==============

WGS84 ↔ NDS coordinates::

    from ndslive.math import Wgs84

    point = Wgs84(lon=11.585, lat=48.137)              # Munich
    nds_x, nds_y = point.to_nds_coordinates()
    back = Wgs84.from_nds_coordinates(nds_x, nds_y)

Packed tile IDs and neighbour traversal::

    from ndslive.math import PackedTileId, MortonCode

    morton = MortonCode.from_nds_coordinates(nds_x, nds_y)
    tile = PackedTileId.from_morton_and_level(morton, level=13)
    sw, ne = tile.south_west_corner(), tile.north_east_corner()
    east_neighbour = tile.east_neighbour()

Bounding-box utilities::

    from ndslive.math import NdsBoundingBox, get_tile_ids_for_bounding_box

    bbox = NdsBoundingBox.from_wgs84_corners(
        sw=Wgs84(11.5, 48.1), ne=Wgs84(11.7, 48.2)
    )
    tile_ids = get_tile_ids_for_bounding_box(
        bbox.sw_x, bbox.sw_y, bbox.ne_x, bbox.ne_y, level=13
    )

What's in this package
======================

Coordinate systems
    :class:`Wgs84` — WGS84 lon/lat/alt point with conversion to/from NDS
    coordinates, arithmetic operators, distance and bearing helpers.

Tile IDs
    :class:`PackedTileId` — NDS Packed Tile ID (Morton + level), with
    geometry accessors (``south_west_corner``, ``center``, …) and
    neighbour traversal (``east_neighbour``, ``north_neighbour``, …).
    :class:`MortonCode` — standalone Z-order encoder/decoder.
    :func:`get_tile_ids_for_bounding_box`,
    :func:`bounding_box_from_tile_ids` — bulk tile enumeration helpers.

Bounding boxes
    :class:`NdsBoundingBox` — dataclass representing a rectangle in NDS
    coordinate space, with ``intersects`` / ``contains`` predicates and
    constructors from a tile or from WGS84 corners.

Geometry layer
    :class:`Polygon` — generic vertex container with ``orientation``
    (with :class:`Orientation` / :class:`PolygonType` enums).
    :class:`Wgs84Polygon` — WGS84 polygon with bounding box (``aa_bb``),
    centroid (``median``) and SAT collision (``collides_with``).
    :class:`Wgs84Aabb` — WGS84 axis-aligned bounding box with corner /
    center accessors, ``contains`` / ``intersects`` and antimeridian
    handling.
    :class:`PolygonTriangulation` — ear-clipping triangulation.
    :class:`Vec2` — raw, un-normalized 2D extent used for AABB sizes.

Version info
    :data:`__version__`.
"""

from .bounding_box import NdsBoundingBox
from .morton import MortonCode
from .polygon import Orientation, Polygon, PolygonType
from .tileid import PackedTileId, bounding_box_from_tile_ids, get_tile_ids_for_bounding_box
from .triangulation import PolygonTriangulation
from .vec2 import Vec2
from .wgs84 import Wgs84
from .wgs84_aabb import Wgs84Aabb
from .wgs84_polygon import Wgs84Polygon

try:
    from ._version import __version__
except ImportError:
    # Fallback for development/editable installs before build
    __version__ = "0.0.0+unknown"


__all__ = [
    # Coordinate systems
    "Wgs84",
    # Tile IDs
    "PackedTileId",
    "MortonCode",
    "get_tile_ids_for_bounding_box",
    "bounding_box_from_tile_ids",
    # Bounding boxes
    "NdsBoundingBox",
    # Geometry layer
    "Polygon",
    "Orientation",
    "PolygonType",
    "Wgs84Polygon",
    "Wgs84Aabb",
    "PolygonTriangulation",
    "Vec2",
    # Version info
    "__version__",
]
