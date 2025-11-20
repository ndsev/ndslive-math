from .morton import MortonCode


class PackedTileId:
    """
    Represents a tile in a hierarchical tiling system.
    Provides methods to extract level, size, and coordinate
    information from the packed tile ID.

    All constructors validate inputs and raise ValueError for invalid tile IDs.
    """
    def __init__(self, value=0):
        self.value = value
        self._validate()
    
    @classmethod
    def from_tile_index(cls, morton_number, level):
        """
        Create a PackedTileId directly from a tile morton number and level.

        This constructs a tile using the morton number as the tile's index
        at the specified level, without any coordinate conversion.

        Args:
            morton_number: The tile's morton number (0 to 2^(2*level+1) - 1)
            level: Tile level (0-15)

        Returns:
            PackedTileId with the specified morton number at the given level

        Raises:
            ValueError: If level or morton_number are out of valid range

        Example:
            >>> tile = PackedTileId.from_tile_index(4, 2)
            >>> tile.morton_number()  # Returns 4
        """
        # Validate level
        if not (0 <= level <= 15):
            raise ValueError(f"Invalid level {level} (must be 0-15)")

        # Validate morton number for this level
        max_morton = (1 << (2 * level + 1)) - 1
        if not (0 <= morton_number <= max_morton):
            raise ValueError(
                f"Invalid morton number {morton_number} for level {level} "
                f"(allowed: 0-{max_morton})"
            )

        value = morton_number + (1 << (16 + level))
        return cls(value)

    @classmethod
    def from_morton_and_level(cls, morton_code, level):
        """
        Create a PackedTileId that contains the point encoded by a MortonCode.

        This method finds the tile at the specified level that contains the
        full-precision NDS coordinates encoded in the MortonCode. The resulting
        tile's morton_number will NOT equal the input morton_code.value() unless
        the point happens to be in that specific tile.

        Note: If you want to create a tile with a specific morton number, use
        from_tile_index() instead.

        Args:
            morton_code: A MortonCode representing full-precision NDS coordinates
            level: Tile level (0-15)

        Returns:
            PackedTileId of the tile containing the encoded point

        Raises:
            ValueError: If level is out of valid range
        """
        # Validate level
        if not (0 <= level <= 15):
            raise ValueError(f"Invalid level {level} (must be 0-15)")

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

    def _validate(self):
        """
        Validates this PackedTileId.

        Raises:
            ValueError: If the tile ID is invalid, with a detailed error message
        """
        min_packed_tile_id = 1 << 16
        if self.value < min_packed_tile_id:
            raise ValueError(
                f"Invalid PackedTileId({self.value}): value must be >= {min_packed_tile_id}"
            )

        tile_level = self.level()
        morton = self.morton_number()
        max_morton = (1 << (2 * tile_level + 1)) - 1

        if morton < 0 or morton > max_morton:
            raise ValueError(
                f"Invalid PackedTileId({self.value}): morton number {morton} "
                f"exceeds valid range for level {tile_level} (allowed: 0-{max_morton})"
            )

    def _deinterleave_morton(self, morton, level):
        """
        Extract X and Y coordinates from morton number.

        In the NDS tiling system, X has (level+1) bits and Y has level bits,
        creating a rectangular grid that is twice as wide as it is tall.

        Args:
            morton: The morton number to deinterleave
            level: The tile level

        Returns:
            Tuple of (x, y) coordinates
        """
        x = y = 0
        # Y has 'level' bits, X has 'level + 1' bits
        # Morton bits are interleaved as: X0 Y0 X1 Y1 ... X{level} Y{level-1} X{level}
        for i in range(level):
            if morton & (1 << (2 * i)):
                x |= (1 << i)
            if morton & (1 << (2 * i + 1)):
                y |= (1 << i)
        # Extract the extra X bit
        if morton & (1 << (2 * level)):
            x |= (1 << level)
        return x, y

    def _interleave_coords(self, x, y, level):
        """
        Create morton number from X and Y coordinates.

        In the NDS tiling system, X has (level+1) bits and Y has level bits.

        Args:
            x: X coordinate (0 to 2^(level+1) - 1)
            y: Y coordinate (0 to 2^level - 1)
            level: The tile level

        Returns:
            The interleaved morton number
        """
        morton = 0
        # Interleave level bits from each coordinate
        for i in range(level):
            if x & (1 << i):
                morton |= (1 << (2 * i))
            if y & (1 << i):
                morton |= (1 << (2 * i + 1))
        # Add the extra X bit
        if x & (1 << level):
            morton |= (1 << (2 * level))
        return morton

    def west_neighbour(self):
        """
        Returns the tile to the west of this tile at the same level.

        Wraps around at the antimeridian (180° longitude) - going west from
        the westernmost tile returns the easternmost tile at the same level.

        Returns:
            PackedTileId of the western neighbor (with wrapping)
        """
        level = self.level()
        morton = self.morton_number()

        # Deinterleave to get X, Y
        x, y = self._deinterleave_morton(morton, level)

        # Move west (decrement X with wrapping)
        # X has (level + 1) bits, so max value is 2^(level+1) - 1
        max_x = (1 << (level + 1)) - 1
        x = (x - 1) & max_x

        # Reinterleave
        new_morton = self._interleave_coords(x, y, level)

        return PackedTileId.from_tile_index(new_morton, level)

    def east_neighbour(self):
        """
        Returns the tile to the east of this tile at the same level.

        Wraps around at the antimeridian (180° longitude) - going east from
        the easternmost tile returns the westernmost tile at the same level.

        Returns:
            PackedTileId of the eastern neighbor (with wrapping)
        """
        level = self.level()
        morton = self.morton_number()

        x, y = self._deinterleave_morton(morton, level)

        # Move east (increment X with wrapping)
        # X has (level + 1) bits, so max value is 2^(level+1) - 1
        max_x = (1 << (level + 1)) - 1
        x = (x + 1) & max_x

        new_morton = self._interleave_coords(x, y, level)
        return PackedTileId.from_tile_index(new_morton, level)

    def south_neighbour(self):
        """
        Returns the tile to the south of this tile at the same level.

        Wraps around at the south pole - going south from the southernmost
        tile returns the northernmost tile at the same level.

        Returns:
            PackedTileId of the southern neighbor (with wrapping)
        """
        level = self.level()
        morton = self.morton_number()

        x, y = self._deinterleave_morton(morton, level)

        # Move south (decrement Y with wrapping)
        # Y has level bits, so max value is 2^level - 1
        max_y = (1 << level) - 1
        y = (y - 1) & max_y

        new_morton = self._interleave_coords(x, y, level)
        return PackedTileId.from_tile_index(new_morton, level)

    def north_neighbour(self):
        """
        Returns the tile to the north of this tile at the same level.

        Wraps around at the north pole - going north from the northernmost
        tile returns the southernmost tile at the same level.

        Returns:
            PackedTileId of the northern neighbor (with wrapping)
        """
        level = self.level()
        morton = self.morton_number()

        x, y = self._deinterleave_morton(morton, level)

        # Move north (increment Y with wrapping)
        # Y has level bits, so max value is 2^level - 1
        max_y = (1 << level) - 1
        y = (y + 1) & max_y

        new_morton = self._interleave_coords(x, y, level)
        return PackedTileId.from_tile_index(new_morton, level)

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


def bounding_box_from_tile_ids(tile_ids):
    """
    Create a tight bounding box from a list of tile IDs.

    This function computes the minimal bounding box in NDS coordinates that
    covers all the specified tiles. The bounding box is guaranteed to be
    tight, meaning it starts at the south-west corner of the westernmost/
    southernmost tile and ends at the north-east corner of the easternmost/
    northernmost tile.

    Important property: When given a single tile ID, the resulting bounding
    box will return only that tile when passed to get_tile_ids_for_bounding_box()
    at the same level.

    Args:
        tile_ids: List of PackedTileId objects or integer tile IDs

    Returns:
        Tuple of (sw_x, sw_y, ne_x, ne_y) in NDS coordinates, representing
        the minimal bounding box that covers all tiles.

    Raises:
        ValueError: If tile_ids list is empty

    Example:
        >>> tile = PackedTileId(545554681)
        >>> bbox = bounding_box_from_tile_ids([tile])
        >>> # bbox will exactly match tile's boundaries
    """
    if not tile_ids:
        raise ValueError("tile_ids list cannot be empty")

    # Ensure we have PackedTileId objects
    tiles = []
    for tid in tile_ids:
        if isinstance(tid, int):
            tiles.append(PackedTileId(tid))
        elif isinstance(tid, PackedTileId):
            tiles.append(tid)
        else:
            raise TypeError(f"Expected int or PackedTileId, got {type(tid)}")

    # Initialize with first tile's bounds
    first_sw_x, first_sw_y = tiles[0].south_west_corner()
    first_ne_x, first_ne_y = tiles[0].north_east_corner()

    min_x = first_sw_x
    min_y = first_sw_y
    max_x = first_ne_x
    max_y = first_ne_y

    # Expand bounds to include all tiles
    for tile in tiles[1:]:
        sw_x, sw_y = tile.south_west_corner()
        ne_x, ne_y = tile.north_east_corner()

        min_x = min(min_x, sw_x)
        min_y = min(min_y, sw_y)
        max_x = max(max_x, ne_x)
        max_y = max(max_y, ne_y)

    # Adjust NE corner: north_east_corner() returns exclusive boundary (first point outside tile)
    # but get_tile_ids_for_bounding_box() treats coordinates as inclusive.
    # Subtract 1 to get the last point inside the tile rather than first point outside.
    return (min_x, min_y, max_x - 1, max_y - 1)
