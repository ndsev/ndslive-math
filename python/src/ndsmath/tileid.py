from .morton import MortonCode


class PackedTileId:
    """
    Represents a tile in a hierarchical tiling system.
    Provides methods to extract level, size, and coordinate information from the packed tile ID.
    """
    def __init__(self, value=0):
        self.value = value

    def level(self):
        level = 0
        tile_id = self.value >> 16
        while tile_id > 1:
            tile_id >>= 1
            level += 1
        return level

    def size(self):
        return 1 << (31 - self.level())

    def center(self):
        x, y = self.south_west_corner()
        half_size = self.size() // 2
        return x + half_size, y + half_size

    def south_west_corner(self):
        morton_number = self.morton_number()
        return MortonCode(morton_number << (63 - (2 * self.level() + 1))).to_nds_coordinates()

    def morton_number(self):
        return self.value & ((1 << 16) - 1)

    def __str__(self):
        return f"PackedTileId(value={self.value})"

    def __eq__(self, other):
        return self.value == other.value

    def __ne__(self, other):
        return self.value != other.value

    def __lt__(self, other):
        return self.value < other.value

    def __int__(self):
        return self.value

    def __str__(self):
        return f"PackedTileId(value={self.value})"
