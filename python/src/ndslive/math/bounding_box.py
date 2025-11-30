"""Bounding box utilities for NDS coordinate space."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Union
    from .tileid import PackedTileId


@dataclass
class NdsBoundingBox:
    """Axis-aligned bounding box in NDS coordinates (32-bit integers).

    NDS coordinates use integers for fast comparisons:
    - X (longitude): 32-bit signed integer
    - Y (latitude): 31-bit signed integer

    Attributes:
        min_x: SW corner longitude (NDS coords)
        min_y: SW corner latitude (NDS coords)
        max_x: NE corner longitude (NDS coords)
        max_y: NE corner latitude (NDS coords)
    """
    min_x: int
    min_y: int
    max_x: int
    max_y: int

    def intersects(self, other: 'NdsBoundingBox') -> bool:
        """Check if this bbox intersects (overlaps) with another.

        Two bounding boxes intersect if they share any area.

        Args:
            other: Another bounding box to check against

        Returns:
            True if the bounding boxes overlap
        """
        return not (
            self.max_x < other.min_x or
            self.min_x > other.max_x or
            self.max_y < other.min_y or
            self.min_y > other.max_y
        )

    def contains(self, other: 'NdsBoundingBox') -> bool:
        """Check if this bbox fully contains another.

        Args:
            other: Another bounding box to check

        Returns:
            True if other is completely inside this bbox
        """
        return (
            self.min_x <= other.min_x and
            self.max_x >= other.max_x and
            self.min_y <= other.min_y and
            self.max_y >= other.max_y
        )

    @classmethod
    def from_tile(cls, tile: 'Union[PackedTileId, int]') -> 'NdsBoundingBox':
        """Create bounding box from a tile ID.

        Args:
            tile: PackedTileId object or integer tile ID

        Returns:
            NdsBoundingBox covering the tile's area
        """
        from .tileid import PackedTileId

        if isinstance(tile, int):
            tile = PackedTileId(tile)
        sw_x, sw_y = tile.south_west_corner()
        ne_x, ne_y = tile.north_east_corner()
        return cls(sw_x, sw_y, ne_x, ne_y)
