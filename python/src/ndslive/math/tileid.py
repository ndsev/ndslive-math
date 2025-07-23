from .morton import MortonCode


class PackedTileId:
    """
    Represents a tile in a hierarchical tiling system.
    Provides methods to extract level, size, and coordinate
    information from the packed tile ID.
    """
    def __init__(self, value=0):
        self.value = value
    
    @classmethod
    def from_morton_and_level(cls, morton_code, level):
        """
        Create a PackedTileId from a MortonCode and level.
        This mirrors the C++ constructor PackedTileId(MortonCode, int level).
        """
        # Get NDS coordinates from morton code
        x_coord, y_coord = morton_code.to_nds_coordinates()
        
        # Handle negative coordinates
        if x_coord < 0:
            x_coord += (1 << 32)
        
        if y_coord < 0:
            y_coord += (1 << 31)
        
        # Calculate tile coordinates
        n_level = 31 - level
        n_x = x_coord >> n_level
        n_y = y_coord >> n_level
        
        # Create morton code from tile coordinates
        temp = MortonCode.from_nds_coordinates(n_x, n_y)
        
        # Calculate packed tile ID value
        value = temp.value() + (1 << (16 + level))
        
        return cls(value)

    def level(self):
        """
        Level of the tile (0..15)
        """
        level = 0
        tile_id = self.value >> 16
        while tile_id > 1:
            tile_id >>= 1
            level += 1
        return level

    def size(self):
        """
        Size of the tile in NDS coordinate units.
        """
        return 1 << (31 - self.level())

    def center(self):
        """
        Returns the center of the tile in NDS coordinates.
        """
        x, y = self.south_west_corner()
        half_size = self.size() // 2
        return x + half_size, y + half_size

    def south_west_corner(self):
        """
        Returns the south-west corner of the tile in NDS coordinates.
        """
        morton_number = self.morton_number()
        return MortonCode(morton_number << (63 - (2 * self.level() + 1))).to_nds_coordinates()

    def north_east_corner(self):
        """
        Returns the north-east corner of the tile in NDS coordinates.
        """
        x, y = self.south_west_corner()
        size = self.size()
        return x + size, y + size

    def morton_number(self):
        """
        Returns the Morton number of the tile, calculated by subtracting
        the level-specific offset from the packed tile ID value.
        """
        tile_level = self.level()
        return self.value - (1 << (16 + tile_level))

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


def get_tile_ids_for_bounding_box(sw_x, sw_y, ne_x, ne_y, level):
    """
    Get all tile IDs that intersect with a bounding box defined by NDS coordinates.
    
    Args:
        sw_x: South-west corner X coordinate (longitude) in NDS coordinates
        sw_y: South-west corner Y coordinate (latitude) in NDS coordinates
        ne_x: North-east corner X coordinate (longitude) in NDS coordinates
        ne_y: North-east corner Y coordinate (latitude) in NDS coordinates
        level: Tile level (0-15)
    
    Returns:
        List of PackedTileId objects that intersect with the bounding box
    """
    tile_ids = []
    
    # Calculate tile size at this level
    tile_size = 1 << (31 - level)
    
    # Calculate tile indices for the bounding box corners
    # We need to handle the coordinate system properly
    start_tile_x = sw_x // tile_size
    start_tile_y = sw_y // tile_size
    end_tile_x = ne_x // tile_size
    end_tile_y = ne_y // tile_size
    
    # Iterate through all tiles in the bounding box
    for tile_y in range(start_tile_y, end_tile_y + 1):
        for tile_x in range(start_tile_x, end_tile_x + 1):
            # Calculate the south-west corner of this tile
            tile_sw_x = tile_x * tile_size
            tile_sw_y = tile_y * tile_size
            
            # Create morton code from the tile's south-west corner
            morton = MortonCode.from_nds_coordinates(tile_sw_x, tile_sw_y)
            
            # Create the packed tile ID
            tile_id = PackedTileId.from_morton_and_level(morton, level)
            tile_ids.append(tile_id)
    
    return tile_ids
