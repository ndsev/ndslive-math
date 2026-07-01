# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from .morton import MortonCode


class PackedTileId:
    """
    Represents a tile in a hierarchical tiling system following the NDS.Live standard.

    Per the NDS.Live standard, tile IDs are signed 32-bit integers. For levels 0-14,
    values are positive. For level 15, values are negative (-2147483648 to -1) because
    the level bit (bit 31) is the sign bit in signed int32 representation.

    Implementation Note:
    Internally, values are stored as unsigned 32-bit integers to enable clean bit
    operations without sign bit complications. Conversion between signed and unsigned
    happens only at the API boundary:
    - Constructor accepts both signed and unsigned representations
    - value property returns signed int32 per NDS.Live standard
    - All internal bit operations work with unsigned representation

    This approach provides a signed API (matching the standard) while keeping internal
    arithmetic simple and efficient.

    Examples:
        # Level 15 tiles have negative values per standard
        >>> tile = PackedTileId.from_tile_index(0, 15)
        >>> print(tile.value)
        -2147483648

        # Constructor accepts negative values (signed representation)
        >>> tile = PackedTileId(-2147483648)
        >>> print(tile.level())
        15
        >>> print(tile.morton_number())
        0

        # Constructor also accepts unsigned representation (same tile)
        >>> tile = PackedTileId(2147483648)
        >>> print(tile.value)  # Always returns signed
        -2147483648

        # Maximum level 15 tile
        >>> tile = PackedTileId.from_tile_index((1 << 31) - 1, 15)
        >>> print(tile.value)
        -1

        # Levels 0-14 have positive values
        >>> tile = PackedTileId.from_tile_index(0, 14)
        >>> print(tile.value)
        1073741824

    All constructors validate inputs and raise ValueError for invalid tile IDs.
    """

    def __init__(self, value: int = 0) -> None:
        """
        Construct a PackedTileId from a tile ID value.

        Accepts both signed and unsigned 32-bit integer representations.
        Per the NDS.Live standard, level 15 tiles have negative values
        (-2147483648 to -1), while levels 0-14 have positive values.

        Args:
            value: Tile ID as signed int32 (negative for level 15) or unsigned int32.
                   Both representations are accepted and produce identical results.

        Examples:
            # Level 15 morton 0 - both representations are equivalent:
            >>> tile1 = PackedTileId(-2147483648)  # Signed representation
            >>> tile2 = PackedTileId(2147483648)   # Unsigned representation
            >>> tile1.value == tile2.value  # Both return -2147483648
            True

        Raises:
            ValueError: If the tile ID is invalid
        """
        # Normalize to unsigned int32 for internal storage
        # This allows clean bit operations without sign complications
        if value < 0:
            # Convert signed int32 to unsigned (e.g., -2147483648 → 2147483648)
            self._value = value + (1 << 32)
        elif value >= (1 << 32):
            # Handle values outside 32-bit range by masking to 32 bits
            self._value = value & 0xFFFFFFFF
        else:
            # Already unsigned, store as-is
            self._value = value

        self._validate()

    @property
    def value(self) -> int:
        """
        Get the tile ID value as signed int32 per NDS.Live standard.

        Returns the tile ID in its signed int32 representation, matching the
        NDS.Live standard. Level 15 tiles return negative values (-2147483648 to -1),
        while levels 0-14 return positive values.

        Returns:
            int: Signed int32 value (negative for level 15, positive for levels 0-14)

        Note:
            Internally, values are stored as unsigned for cleaner bit operations.
            This property performs the conversion from unsigned to signed at the API boundary.

        Example:
            >>> tile = PackedTileId.from_tile_index(0, 15)
            >>> tile.value
            -2147483648
            >>> tile = PackedTileId.from_tile_index(0, 14)
            >>> tile.value
            1073741824
        """
        # Convert unsigned to signed int32 for API
        if self._value >= (1 << 31):
            # Value has bit 31 set, so it's negative in signed int32
            return self._value - (1 << 32)
        # Value is positive in both signed and unsigned
        return self._value

    @classmethod
    def from_value(cls, value: int) -> PackedTileId:
        """Create a PackedTileId from the signed NDS.Live public value."""
        return cls(value)

    @classmethod
    def from_tile_index(cls, morton_number: int, level: int) -> PackedTileId:
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
                f"Invalid morton number {morton_number} for level {level} (allowed: 0-{max_morton})"
            )

        value = morton_number + (1 << (16 + level))
        return cls(value)

    @classmethod
    def from_morton_and_level(cls, morton_code: MortonCode, level: int) -> PackedTileId:
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
            x_coord += 1 << 32

        if y_coord < 0:
            y_coord += 1 << 31

        # Calculate tile coordinates
        n_level = 31 - level
        n_x = x_coord >> n_level
        n_y = y_coord >> n_level

        # Create morton code from tile coordinates
        temp = MortonCode.from_nds_coordinates(n_x, n_y)

        # Calculate packed tile ID value
        value = temp.value() + (1 << (16 + level))

        return cls(value)

    @classmethod
    def from_tile_xy(cls, x: int, y: int, level: int) -> PackedTileId:
        """Create a tile from tile-grid coordinates at the given level.

        ``x`` is in ``[0, 2^(level+1)-1]`` and ``y`` is in
        ``[0, 2^level-1]``. Coordinates use the NDS Morton tile-grid order and
        are inverse to :meth:`x` and :meth:`y`.
        """
        if not (0 <= level <= 15):
            raise ValueError(f"Invalid level {level} (must be 0-15)")
        max_x = (1 << (level + 1)) - 1
        max_y = (1 << level) - 1
        if not (0 <= x <= max_x and 0 <= y <= max_y):
            raise ValueError(
                f"Invalid tile coordinates ({x}, {y}) for level {level} "
                f"(allowed x: 0-{max_x}, y: 0-{max_y})"
            )
        return cls.from_tile_index(cls._interleave_coords(x, y, level), level)

    @classmethod
    def from_nds_coordinates(cls, x: int, y: int, level: int) -> PackedTileId:
        """Create the tile at ``level`` that contains the given NDS coordinate."""
        return cls.from_morton_and_level(MortonCode.from_nds_coordinates(x, y), level)

    @classmethod
    def from_wgs84(cls, longitude: float, latitude: float, level: int) -> PackedTileId:
        """Create the tile at ``level`` that contains the given WGS84 coordinate."""
        from .wgs84 import Wgs84

        x, y = Wgs84(longitude, latitude).to_nds_coordinates()
        return cls.from_nds_coordinates(x, y, level)

    def level(self) -> int:
        """
        Level of the tile (0..15)
        """
        level = 0
        tile_id = self._value >> 16
        while tile_id > 1:
            tile_id >>= 1
            level += 1
        return level

    def size(self) -> int:
        """
        Size of the tile in NDS coordinate units.
        """
        return 1 << (31 - self.level())

    def dimensions_in_meters(self) -> tuple[float, float]:
        """
        Get tile dimensions in meters.

        Returns:
            Tuple of (width_meters, height_meters) calculated at the tile's center latitude.

        Note:
            Dimensions vary by latitude - tiles are largest at the equator and shrink toward poles.
            Width (longitude) is affected by cos(latitude), height (latitude) remains constant.
        """
        from .wgs84 import Wgs84

        center_x, center_y = self.center()
        center_wgs = Wgs84.from_nds_coordinates(center_x, center_y)
        tile_size = self.size()

        return Wgs84.nds_distance_to_meters(tile_size, tile_size, center_wgs.y)

    def center(self) -> tuple[int, int]:
        """
        Returns the center of the tile in NDS coordinates.
        """
        x, y = self.south_west_corner()
        half_size = self.size() // 2
        return x + half_size, y + half_size

    def south_west_corner(self) -> tuple[int, int]:
        """
        Returns the south-west corner of the tile in NDS coordinates.
        """
        morton_number = self.morton_number()
        return MortonCode(morton_number << (63 - (2 * self.level() + 1))).to_nds_coordinates()

    def north_east_corner(self) -> tuple[int, int]:
        """
        Returns the north-east corner of the tile in NDS coordinates.
        """
        x, y = self.south_west_corner()
        size = self.size()
        return x + size, y + size

    def morton_number(self) -> int:
        """
        Returns the Morton number of the tile, calculated by subtracting
        the level-specific offset from the packed tile ID value.
        """
        tile_level = self.level()
        return self._value - (1 << (16 + tile_level))

    def x(self) -> int:
        """Tile-grid X coordinate at this tile's level."""
        return self._deinterleave_morton(self.morton_number(), self.level())[0]

    def y(self) -> int:
        """Tile-grid Y coordinate at this tile's level."""
        return self._deinterleave_morton(self.morton_number(), self.level())[1]

    def _validate(self) -> None:
        """
        Validates this PackedTileId.

        Internal validation works with unsigned storage (_value), but error messages
        show the signed API value for user clarity.

        Raises:
            ValueError: If the tile ID is invalid, with a detailed error message
        """
        min_packed_tile_id = 1 << 16
        # Internal value is unsigned, so simple comparison works
        # (level 15 tiles have _value >= 2^31 which is > min_packed_tile_id)
        if self._value < min_packed_tile_id:
            raise ValueError(
                f"Invalid PackedTileId({self.value}): value must be >= {min_packed_tile_id} "
                f"or negative for level 15"
            )

        tile_level = self.level()
        morton = self.morton_number()
        max_morton = (1 << (2 * tile_level + 1)) - 1

        if morton < 0 or morton > max_morton:
            raise ValueError(
                f"Invalid PackedTileId({self.value}): morton number {morton} "
                f"exceeds valid range for level {tile_level} (allowed: 0-{max_morton})"
            )

    @staticmethod
    def _deinterleave_morton(morton: int, level: int) -> tuple[int, int]:
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
                x |= 1 << i
            if morton & (1 << (2 * i + 1)):
                y |= 1 << i
        # Extract the extra X bit
        if morton & (1 << (2 * level)):
            x |= 1 << level
        return x, y

    @staticmethod
    def _interleave_coords(x: int, y: int, level: int) -> int:
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
                morton |= 1 << (2 * i)
            if y & (1 << i):
                morton |= 1 << (2 * i + 1)
        # Add the extra X bit
        if x & (1 << level):
            morton |= 1 << (2 * level)
        return morton

    def west_neighbour(self) -> PackedTileId:
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

    def east_neighbour(self) -> PackedTileId:
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

    def south_neighbour(self) -> PackedTileId:
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

    def north_neighbour(self) -> PackedTileId:
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

    def print_with_neighbors(self, radius: int = 1) -> None:
        """
        Print a debug visualization showing this tile and its neighbors.

        Shows the current tile's binary encoding first, then displays a grid of neighbors.
        Grid size depends on radius:
        - radius=1: 3x3 grid (default, current + 8 immediate neighbors)
        - radius=2: 5x5 grid (current + 24 neighbors within 2 tiles)
        - radius=3: 7x7 grid (current + 48 neighbors within 3 tiles)

        Args:
            radius (int): How many tiles away to show in each direction (default: 1)

        Each grid cell displays:
        - Line 1: TileID: <value>
        - Line 2: Tile Number: <morton>
        """
        level = self.level()
        bits = 2 * level + 1

        # Helper to get hierarchical binary representation
        def get_binary_label(morton_num):
            """
            Generate hierarchical address showing path through quad-tree.
            Level 0: 1 bit (0 or 1)
            Each subsequent level: 2 bits (00, 01, 10, 11)
            Example: level 2 tile → "0-11-01" means:
              - Level 0: tile 0
              - Level 1: tile 11 within 0
              - Level 2: tile 01 within 0-11
            """
            if level == 0:
                # Level 0 has only 1 bit
                return str(morton_num)

            parts = []

            # Extract bits from MSB to LSB
            # Level 0: 1 bit
            level0_bit = (morton_num >> (bits - 1)) & 1
            parts.append(str(level0_bit))

            # Subsequent levels: 2 bits each
            for lev in range(1, level + 1):
                # Extract 2 bits for this level
                shift_amount = bits - 1 - (2 * lev)
                two_bits = (morton_num >> shift_amount) & 0b11
                parts.append(format(two_bits, "02b"))

            return "-".join(parts)

        # Print header with current tile info
        print(f"\nTileID: {self.value}")
        print(f"Level: {level}")
        print(f"Tile Number: {self.morton_number()}")
        print(f"Bits for index: {bits}")
        print(f"Binary Tile Number: {get_binary_label(self.morton_number())}")

        # Print coordinate information (NDS coords with WGS84 in parentheses)
        from .wgs84 import Wgs84

        center_x, center_y = self.center()
        sw_x, sw_y = self.south_west_corner()
        ne_x, ne_y = self.north_east_corner()

        # Convert to WGS84 for readability
        center_wgs = Wgs84.from_nds_coordinates(center_x, center_y)
        sw_wgs = Wgs84.from_nds_coordinates(sw_x, sw_y)
        ne_wgs = Wgs84.from_nds_coordinates(ne_x, ne_y)

        print(f"Center: ({center_x}, {center_y}) ({center_wgs.x:.6f}°, {center_wgs.y:.6f}°)")
        print(f"SW Corner: ({sw_x}, {sw_y}) ({sw_wgs.x:.6f}°, {sw_wgs.y:.6f}°)")
        print(f"NE Corner: ({ne_x}, {ne_y}) ({ne_wgs.x:.6f}°, {ne_wgs.y:.6f}°)")

        # Print tile dimensions in real-world units
        def format_distance(meters):
            """Format distance with appropriate units."""
            if meters < 1000:
                return f"{meters:.0f} m"
            else:
                return f"{meters / 1000:.1f} km"

        # Dimensions at tile's center latitude
        width_m, height_m = self.dimensions_in_meters()
        print(
            f"Tile Size: {format_distance(width_m)} × {format_distance(height_m)} (at {center_wgs.y:.1f}°)"
        )

        # Dimensions at equator for reference
        tile_size = self.size()
        width_eq, height_eq = Wgs84.nds_distance_to_meters(tile_size, tile_size, 0.0)
        print(f"At Equator: {format_distance(width_eq)} × {format_distance(height_eq)}")
        print()

        # Build grid dynamically based on radius
        # Grid goes from -radius to +radius in both X and Y directions
        grid_size = 2 * radius + 1
        grid = []

        for dy in range(-radius, radius + 1):
            row = []
            for dx in range(-radius, radius + 1):
                # Start from center tile
                tile = self

                # Move horizontally (east/west)
                for _ in range(abs(dx)):
                    if dx > 0:
                        tile = tile.east_neighbour()
                    else:
                        tile = tile.west_neighbour()

                # Move vertically (north/south)
                for _ in range(abs(dy)):
                    if dy > 0:
                        tile = tile.north_neighbour()
                    else:
                        tile = tile.south_neighbour()

                row.append(tile)
            grid.append(row)

        # Determine column width to make cells square
        # Each cell shows: TileID value and (morton) in parentheses
        max_tileid_len = max(len(str(tile.value)) for row in grid for tile in row)
        max_morton_len = max(len(f"({tile.morton_number()})") for row in grid for tile in row)
        col_width = max(max_tileid_len, max_morton_len) + 4

        # Print grid with directional labels
        border = "+" + ("-" * col_width + "+") * grid_size

        # Print "Neighbors:" label
        print("Neighbors:")

        # North label and border should align with grid (2 spaces for west labels)
        north_label = "North".center(len(border))
        print(f"  {north_label}")
        print(f"  {border}")

        # West/East labels shown vertically (centered on the grid)
        center_row = radius
        for row_idx, row in enumerate(grid):
            # Determine left/right labels for this row
            # Position "West" and "East" in the middle of the grid
            if row_idx == center_row - 1:
                left_label1 = "  "
                left_label2 = "W "
                right_label1 = "  "
                right_label2 = " E"
            elif row_idx == center_row:
                left_label1 = "e "
                left_label2 = "s "
                right_label1 = " a"
                right_label2 = " s"
            elif row_idx == center_row + 1:
                left_label1 = "t "
                left_label2 = "  "
                right_label1 = " t"
                right_label2 = "  "
            else:
                # Other rows: no labels
                left_label1 = "  "
                left_label2 = "  "
                right_label1 = "  "
                right_label2 = "  "

            # Line 1: TileID values (or "CURRENT" for center tile)
            line1 = left_label1 + "|"
            for col_idx, tile in enumerate(row):
                if row_idx == radius and col_idx == radius:
                    # Center tile: show "CURRENT"
                    tileid_str = "CURRENT"
                else:
                    tileid_str = str(tile.value)
                line1 += tileid_str.center(col_width) + "|"
            line1 += right_label1
            print(line1)

            # Line 2: Tile Number (or "TILE" for center tile)
            line2 = left_label2 + "|"
            for col_idx, tile in enumerate(row):
                if row_idx == radius and col_idx == radius:
                    # Center tile: show "TILE"
                    morton_str = "TILE"
                else:
                    morton_str = f"({tile.morton_number()})"
                line2 += morton_str.center(col_width) + "|"
            line2 += right_label2
            print(line2)

            # Row border
            print(f"  {border}  ")

        # South label should align with grid
        south_label = "South".center(len(border))
        print(f"  {south_label}")

    def __str__(self) -> str:
        return f"PackedTileId(value={self.value})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PackedTileId):
            return NotImplemented
        return self._value == other._value

    def __ne__(self, other: object) -> bool:
        if not isinstance(other, PackedTileId):
            return NotImplemented
        return self._value != other._value

    def __lt__(self, other: PackedTileId) -> bool:
        return self._value < other._value

    def __int__(self) -> int:
        """
        Convert to integer (returns signed int32 per NDS.Live standard).
        """
        return self.value


def get_tile_ids_for_bounding_box(
    sw_x: int, sw_y: int, ne_x: int, ne_y: int, level: int
) -> list[PackedTileId]:
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


def bounding_box_from_tile_ids(
    tile_ids: list[PackedTileId | int],
) -> tuple[int, int, int, int]:
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
