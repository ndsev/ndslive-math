# SPDX-License-Identifier: BSD-3-Clause
import unittest

from ndslive.math import MortonCode, NdsBoundingBox, PackedTileId, Wgs84
from ndslive.math.tileid import bounding_box_from_tile_ids, get_tile_ids_for_bounding_box


def print_level1_grid(current_morton, neighbor_morton=None, direction=""):
    """
    Print a visual representation of level 1 tiling grid.

    Level 1 has 8 tiles (morton 0-7) arranged geographically with
    the antimeridian between columns 2 and 3.

    Geographic layout (as seen on world map):
        Western Hemisphere (X=2,3) | Eastern Hemisphere (X=0,1)

    Args:
        current_morton: Morton number of current tile (0-7)
        neighbor_morton: Morton number of expected neighbor (0-7) or None
        direction: Direction of neighbor (N/S/E/W)
    """
    # Geographic arrangement: West (X=2,3) then East (X=0,1)
    # Level 1 tile labels (format: level0-level1)
    labels = [
        ["1-00", "1-01", "0-00", "0-01"],  # Y=0 (top row)
        ["1-10", "1-11", "0-10", "0-11"],  # Y=1 (bottom row)
    ]
    # Morton numbers for each position (geographic order)
    morton_grid = [
        [4, 5, 0, 1],  # Y=0: X=2,3,0,1
        [6, 7, 2, 3],  # Y=1: X=2,3,0,1
    ]

    print(
        f"\nLevel 1 Grid - Current tile: {current_morton}, "
        f"Expected {direction} neighbor: {neighbor_morton}"
    )
    print("=" * 60)

    # Top border
    print("  +-------+-------++-------+-------+")

    for row in range(2):
        # Tile labels row
        line = "  |"
        for col in range(4):
            morton = morton_grid[row][col]
            label = labels[row][col]
            if morton == current_morton:
                line += f" [{label}]|"
            elif morton == neighbor_morton:
                line += f" *{label}*|"
            else:
                line += f"  {label} |"
        print(line)

        # Morton numbers row
        line = "  |"
        for col in range(4):
            morton = morton_grid[row][col]
            if morton == current_morton:
                line += "  [X]  |"
            elif morton == neighbor_morton:
                line += "  [*]  |"
            else:
                line += f"   {morton}   |"
        print(line)

        # Row separator (use || between hemispheres)
        if row == 0:
            print("  +-------+-------++-------+-------+")
        else:
            print("  +-------+-------++-------+-------+")
    print()


class TestWgs84(unittest.TestCase):
    def test_initialization(self):
        point = Wgs84(lon=10.0, lat=20.0, alt=30.0)
        self.assertEqual(point.x, 10.0)
        self.assertEqual(point.y, 20.0)
        self.assertEqual(point.z, 30.0)

    def test_equality_with_foreign_type(self):
        """__eq__ returns NotImplemented for non-Wgs84 operands (so they compare unequal)."""
        point = Wgs84(13.4, 52.5)
        self.assertNotEqual(point, 42)
        self.assertNotEqual(point, "not a point")
        # The dunder itself signals NotImplemented so Python can try the reflected op.
        self.assertIs(point.__eq__(42), NotImplemented)

    def test_normalization_basic(self):
        # Test basic normalization cases from original test
        point = Wgs84(lon=190.0, lat=100.0)
        self.assertLess(point.x, 180.0)
        self.assertGreaterEqual(point.x, -180.0)
        self.assertAlmostEqual(point.y, 90.0 - Wgs84.LAT_NDS_DELTA, places=12)

        point = Wgs84(lon=-190.0, lat=-100.0)
        self.assertLess(point.x, 180.0)
        self.assertGreaterEqual(point.x, -180.0)
        self.assertEqual(point.y, -90.0)

    def test_normalization_detailed(self):
        """Test detailed normalization logic."""
        # Test longitude normalization
        # Within range
        self.assertAlmostEqual(Wgs84(10.0, 0).x, 10.0, places=12)
        self.assertAlmostEqual(Wgs84(-10.0, 0).x, -10.0, places=12)
        # Boundaries
        self.assertAlmostEqual(Wgs84(-180.0, 0).x, -180.0, places=12)  # Should stay -180
        self.assertAlmostEqual(
            Wgs84(180.0, 0).x, 180.0 - Wgs84.LON_NDS_DELTA, places=12
        )  # Should become ~180 - delta
        self.assertAlmostEqual(
            Wgs84(180.0 - Wgs84.LON_NDS_DELTA / 2, 0).x, 180.0 - Wgs84.LON_NDS_DELTA, places=12
        )  # Close to 180
        # Wrapping
        self.assertAlmostEqual(Wgs84(190.0, 0).x, -170.0, places=12)  # 190 -> -170
        self.assertAlmostEqual(Wgs84(-190.0, 0).x, 170.0, places=12)  # -190 -> 170
        self.assertAlmostEqual(Wgs84(370.0, 0).x, 10.0, places=12)  # 370 -> 10
        self.assertAlmostEqual(Wgs84(-370.0, 0).x, -10.0, places=12)  # -370 -> -10
        self.assertAlmostEqual(
            Wgs84(540.0, 0).x, 180.0 - Wgs84.LON_NDS_DELTA, places=12
        )  # 540 -> 180 -> ~180 - delta
        self.assertAlmostEqual(Wgs84(-540.0, 0).x, -180.0, places=12)  # -540 -> -180

        # Test latitude normalization
        # Within range
        self.assertAlmostEqual(Wgs84(0, 80.0).y, 80.0, places=12)
        self.assertAlmostEqual(Wgs84(0, -80.0).y, -80.0, places=12)
        # Boundaries and clamping
        self.assertAlmostEqual(Wgs84(0, -90.0).y, -90.0, places=12)  # Min lat
        self.assertAlmostEqual(
            Wgs84(0, 90.0).y, 90.0 - Wgs84.LAT_NDS_DELTA, places=12
        )  # Max lat becomes 90 - delta
        self.assertAlmostEqual(
            Wgs84(0, 90.0 - Wgs84.LAT_NDS_DELTA / 2).y, 90.0 - Wgs84.LAT_NDS_DELTA, places=12
        )  # Close to 90
        self.assertAlmostEqual(
            Wgs84(0, 100.0).y, 90.0 - Wgs84.LAT_NDS_DELTA, places=12
        )  # Above 90 - delta gets clamped
        self.assertAlmostEqual(Wgs84(0, -100.0).y, -90.0, places=12)  # Below -90 gets clamped

    def test_distance_calculation(self):
        point1 = Wgs84(0, 0)
        point2 = Wgs84(1, 1)
        distance = point1.distance_to(point2)
        self.assertGreater(distance, 0)

    def test_nds_coordinate_uses_floor(self):
        """Test that to_nds_coordinates uses floor (toward -infinity) not truncate."""
        # Floor should round toward -infinity, not toward zero (truncate)
        # This matters for negative coordinates near tile boundaries

        # Test positive coordinates (floor and truncate behave the same)
        positive = Wgs84(0.0001, 0.0001)
        px, py = positive.to_nds_coordinates()
        self.assertGreater(px, 0)
        self.assertGreater(py, 0)

        # Test negative coordinates (floor rounds down, truncate rounds toward zero)
        negative = Wgs84(-0.0001, -0.0001)
        nx, ny = negative.to_nds_coordinates()
        self.assertLess(nx, 0)
        self.assertLess(ny, 0)

        # Verify floor behavior: for tiny negative value, result should be -1, not 0
        tiny_neg = Wgs84(-1e-10, -1e-10)
        tnx, tny = tiny_neg.to_nds_coordinates()
        self.assertEqual(tnx, -1)  # floor(-tiny) = -1, not 0
        self.assertEqual(tny, -1)

        # Roundtrip test: convert back and verify we're in the same "cell"
        back_positive = Wgs84.from_nds_coordinates(px, py)
        back_negative = Wgs84.from_nds_coordinates(nx, ny)
        self.assertGreaterEqual(back_positive.x, 0.0)
        self.assertLess(back_negative.x, 0.0)

    def test_nds_coordinate_conversion(self):
        # Test conversion at origin (0, 0)
        origin = Wgs84(0.0, 0.0)
        x_nds, y_nds = origin.to_nds_coordinates()
        self.assertEqual(x_nds, 0)
        self.assertEqual(y_nds, 0)
        wgs_back = Wgs84.from_nds_coordinates(x_nds, y_nds)
        self.assertAlmostEqual(wgs_back.x, 0.0, places=10)
        self.assertAlmostEqual(wgs_back.y, 0.0, places=10)

        # Test conversion at maximum valid coordinates
        max_point = Wgs84(179.999999, 89.999999)  # Just under 180, 90
        x_nds, y_nds = max_point.to_nds_coordinates()
        wgs_back = Wgs84.from_nds_coordinates(x_nds, y_nds)
        self.assertAlmostEqual(wgs_back.x, max_point.x, places=6)
        self.assertAlmostEqual(wgs_back.y, max_point.y, places=6)

        # Test conversion at minimum valid coordinates
        min_point = Wgs84(-180.0, -90.0)
        x_nds, y_nds = min_point.to_nds_coordinates()
        wgs_back = Wgs84.from_nds_coordinates(x_nds, y_nds)
        self.assertAlmostEqual(wgs_back.x, min_point.x, places=6)
        self.assertAlmostEqual(wgs_back.y, min_point.y, places=6)

        # Test conversion at a specific location (e.g., Berlin)
        berlin = Wgs84(13.404954, 52.520008)
        x_nds, y_nds = berlin.to_nds_coordinates()
        wgs_back = Wgs84.from_nds_coordinates(x_nds, y_nds)
        self.assertAlmostEqual(wgs_back.x, berlin.x, places=6)
        self.assertAlmostEqual(wgs_back.y, berlin.y, places=6)

    def test_nds_coordinate_bounds(self):
        # Test that NDS coordinates stay within valid bounds
        max_x_nds = (1 << 32) - 1  # Maximum 32-bit value
        max_y_nds = (1 << 31) - 1  # Maximum 31-bit value

        # Convert maximum NDS coordinates back to WGS84
        wgs = Wgs84.from_nds_coordinates(max_x_nds, max_y_nds)
        self.assertLess(wgs.x, 180.0)
        self.assertLess(wgs.y, 90.0)

        # Convert minimum NDS coordinates back to WGS84
        wgs = Wgs84.from_nds_coordinates(0, -(1 << 31))
        self.assertGreaterEqual(wgs.x, -180.0)
        self.assertGreaterEqual(wgs.y, -90.0)


class TestPackedTileId(unittest.TestCase):
    def test_levels(self):
        """Port of 'PackedTileId levels' test"""
        for level in range(1, 16):
            # Create tile-id from level 1 to 15 and check level
            tile = PackedTileId(value=(1 << (level + 16)))
            self.assertEqual(tile.level(), level)

    def test_tile_number(self):
        """Port of 'PackedTileId tile number' test"""
        TILE_LEVEL_13 = 13
        LEVEL13_TILE_LEN_NDS_UNITS = 1 << (32 - (TILE_LEVEL_13 + 1))
        size = LEVEL13_TILE_LEN_NDS_UNITS

        test_data = [
            (1 * size // 2, 1 * size // 2, TILE_LEVEL_13, 0),
            (3 * size // 2, 1 * size // 2, TILE_LEVEL_13, 1),
            (1 * size // 2, 3 * size // 2, TILE_LEVEL_13, 2),
            (3 * size // 2, 3 * size // 2, TILE_LEVEL_13, 3),
        ]

        for _, _, level, expected_tile_num in test_data:
            tile_id = PackedTileId(value=expected_tile_num + (1 << (level + 16)))
            self.assertEqual(tile_id.morton_number(), expected_tile_num)

    def test_corners(self):
        """Port of 'PackedTileId corners' test"""
        TILE_LEVEL_13 = 13
        LEVEL13_TILE_LEN_NDS_UNITS = 1 << (31 - TILE_LEVEL_13)

        ref_tile = PackedTileId(value=(1 << (TILE_LEVEL_13 + 16)))

        # Test north east corner
        ne_x, ne_y = ref_tile.north_east_corner()
        self.assertEqual(ne_x, LEVEL13_TILE_LEN_NDS_UNITS)
        self.assertEqual(ne_y, LEVEL13_TILE_LEN_NDS_UNITS)

        # Test south west corner
        sw_x, sw_y = ref_tile.south_west_corner()
        self.assertEqual(sw_x, 0)
        self.assertEqual(sw_y, 0)

    def test_wgs84_inspection_helpers(self):
        """PackedTileId exposes lon/lat helpers without WGS84 edge normalization."""
        tile = PackedTileId.from_tile_xy(3, 1, 1)
        self.assertEqual(tile.center_wgs84(), (-45.0, -45.0))
        self.assertEqual(tile.south_west_wgs84(), (-90.0, -90.0))
        self.assertEqual(tile.north_east_wgs84(), (0.0, 0.0))
        self.assertEqual(tile.wgs84_size(), (90.0, 90.0))
        self.assertEqual(PackedTileId.wgs84_from_nds_coordinates(1 << 31, 1 << 30), (180.0, 90.0))

        world_edge = PackedTileId.from_tile_xy(1, 0, 0)
        self.assertEqual(world_edge.center_wgs84(), (-90.0, 90.0))
        self.assertEqual(world_edge.north_east_wgs84(), (0.0, 180.0))

    def test_from_tile_index(self):
        """Test creating a tile directly from morton number and level."""
        # Test basic case - the original bug report
        tile = PackedTileId.from_tile_index(4, 2)
        self.assertEqual(tile.morton_number(), 4)
        self.assertEqual(tile.level(), 2)

        # Test various levels and morton numbers
        test_cases = [
            (0, 1),  # First tile at level 1
            (3, 1),  # Last tile at level 1 (4^1 - 1 = 3)
            (0, 13),  # First tile at level 13
            (15, 2),  # Last tile at level 2 (4^2 - 1 = 15)
            (100, 10),  # Arbitrary tile at level 10
        ]

        for morton_number, level in test_cases:
            with self.subTest(morton_number=morton_number, level=level):
                tile = PackedTileId.from_tile_index(morton_number, level)
                self.assertEqual(tile.morton_number(), morton_number)
                self.assertEqual(tile.level(), level)

    def test_from_tile_index_roundtrip(self):
        """Test that from_tile_index produces valid tiles with correct corners."""
        tile = PackedTileId.from_tile_index(4, 2)

        # Get corners
        sw_x, sw_y = tile.south_west_corner()
        ne_x, ne_y = tile.north_east_corner()

        # Tile size at level 2
        expected_size = 1 << (31 - 2)
        self.assertEqual(tile.size(), expected_size)

        # Verify tile dimensions
        self.assertEqual(ne_x - sw_x, expected_size)
        self.assertEqual(ne_y - sw_y, expected_size)

    def test_validation_exceptions(self):
        """Test that invalid tile IDs raise ValueError with helpful messages."""
        # Valid tiles should not raise
        PackedTileId(1 << 16)  # Level 0, morton 0
        PackedTileId((1 << 16) + 1)  # Level 0, morton 1
        PackedTileId(1 << 17)  # Level 1, morton 0
        PackedTileId((1 << 18) + 15)  # Level 2, morton 15 (max)

        # Invalid tiles - value too small
        with self.assertRaises(ValueError) as ctx:
            PackedTileId(0)
        self.assertIn("must be >=", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            PackedTileId(100)
        self.assertIn("must be >=", str(ctx.exception))

        # Invalid tiles - morton number exceeds max for level
        # Level 0 max morton = 2^1 - 1 = 1, so morton 2 is invalid
        with self.assertRaises(ValueError) as ctx:
            PackedTileId((1 << 16) + 2)
        self.assertIn("morton number", str(ctx.exception))
        self.assertIn("level 0", str(ctx.exception))

        # Level 2 max morton = 2^5 - 1 = 31, so morton 32 is invalid
        with self.assertRaises(ValueError) as ctx:
            PackedTileId((1 << 18) + 32)
        self.assertIn("morton number", str(ctx.exception))
        self.assertIn("level 2", str(ctx.exception))

        # The user's case: 262177 = 262144 + 33 (level 2, morton 33)
        with self.assertRaises(ValueError) as ctx:
            PackedTileId(262177)
        self.assertIn("33", str(ctx.exception))
        self.assertIn("level 2", str(ctx.exception))
        self.assertIn("0-31", str(ctx.exception))

    def test_from_tile_index_validation(self):
        """Test that from_tile_index validates inputs."""
        # Valid construction should work
        tile = PackedTileId.from_tile_index(4, 2)
        self.assertEqual(tile.morton_number(), 4)

        # Invalid level
        with self.assertRaises(ValueError) as ctx:
            PackedTileId.from_tile_index(0, -1)
        self.assertIn("level", str(ctx.exception).lower())

        with self.assertRaises(ValueError) as ctx:
            PackedTileId.from_tile_index(0, 16)
        self.assertIn("level", str(ctx.exception).lower())

        # Invalid morton number for level
        with self.assertRaises(ValueError) as ctx:
            PackedTileId.from_tile_index(33, 2)  # Max is 31 for level 2
        self.assertIn("morton number", str(ctx.exception))
        self.assertIn("33", str(ctx.exception))
        self.assertIn("level 2", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            PackedTileId.from_tile_index(-1, 2)
        self.assertIn("morton number", str(ctx.exception))

    def test_added_factories_and_grid_coordinates(self):
        """Test added PackedTileId factory helpers and grid accessors."""
        tile = PackedTileId.from_tile_xy(3, 1, 1)
        self.assertEqual(tile.value, 131079)
        self.assertEqual(tile.x(), 3)
        self.assertEqual(tile.y(), 1)
        self.assertEqual(PackedTileId.from_value(tile.value).value, tile.value)

        from_nds = PackedTileId.from_nds_coordinates(-65537, -65537, 15)
        from_wgs = PackedTileId.from_wgs84(-0.005493205972015858, -0.005493205972015858, 15)
        self.assertEqual(from_nds.value, -4)
        self.assertEqual(from_wgs.value, -4)

    def test_added_factory_validation(self):
        """Test validation in added PackedTileId factory helpers."""
        with self.assertRaises(ValueError):
            PackedTileId.from_value(0)
        with self.assertRaises(ValueError):
            PackedTileId.from_tile_xy(0, 0, -1)
        with self.assertRaises(ValueError):
            PackedTileId.from_tile_xy(4, 0, 1)
        with self.assertRaises(ValueError):
            PackedTileId.from_tile_xy(0, 2, 1)
        with self.assertRaises(ValueError):
            PackedTileId.from_nds_coordinates(0, 0, 16)
        with self.assertRaises(ValueError):
            PackedTileId.from_wgs84(0.0, 0.0, 16)

    def test_from_morton_and_level_validation(self):
        """Test that from_morton_and_level validates level."""
        from ndslive.math import MortonCode

        # Valid construction should work
        morton = MortonCode.from_nds_coordinates(100, 100)
        tile = PackedTileId.from_morton_and_level(morton, 5)
        self.assertEqual(tile.level(), 5)

        # Invalid level
        with self.assertRaises(ValueError) as ctx:
            PackedTileId.from_morton_and_level(morton, -1)
        self.assertIn("level", str(ctx.exception).lower())

        with self.assertRaises(ValueError) as ctx:
            PackedTileId.from_morton_and_level(morton, 16)
        self.assertIn("level", str(ctx.exception).lower())

    def test_neighbour_functions_basic(self):
        """Test basic neighbour traversal."""
        # Create a tile at level 2, morton number 0 (SW corner of world)
        tile = PackedTileId.from_tile_index(0, 2)
        self.assertEqual(tile.level(), 2)

        # Get neighbours
        east_tile = tile.east_neighbour()
        north_tile = tile.north_neighbour()

        # Neighbours should be at same level
        self.assertEqual(east_tile.level(), 2)
        self.assertEqual(north_tile.level(), 2)

        # Neighbours should be different tiles
        self.assertNotEqual(tile.value, east_tile.value)
        self.assertNotEqual(tile.value, north_tile.value)

        # Going back should return to original
        self.assertEqual(east_tile.west_neighbour().value, tile.value)
        self.assertEqual(north_tile.south_neighbour().value, tile.value)

    def test_neighbour_functions_roundtrip(self):
        """Test that going in opposite directions returns to original tile."""
        test_tiles = [
            PackedTileId.from_tile_index(0, 5),
            PackedTileId.from_tile_index(100, 10),
            PackedTileId.from_tile_index(7, 3),
            PackedTileId(545554681),  # Real Munich tile
        ]

        for tile in test_tiles:
            with self.subTest(tile_value=tile.value):
                # East-West roundtrip
                self.assertEqual(tile.east_neighbour().west_neighbour().value, tile.value)
                self.assertEqual(tile.west_neighbour().east_neighbour().value, tile.value)

                # North-South roundtrip
                self.assertEqual(tile.north_neighbour().south_neighbour().value, tile.value)
                self.assertEqual(tile.south_neighbour().north_neighbour().value, tile.value)

    def test_neighbour_spatial_relationship(self):
        """Test that neighbours have correct spatial relationships."""
        tile = PackedTileId.from_tile_index(5, 3)
        tile_sw_x, tile_sw_y = tile.south_west_corner()
        tile_size = tile.size()

        # East neighbour should be shifted east by tile_size
        east_tile = tile.east_neighbour()
        east_sw_x, east_sw_y = east_tile.south_west_corner()
        self.assertEqual(east_sw_x, tile_sw_x + tile_size)
        self.assertEqual(east_sw_y, tile_sw_y)

        # North neighbour should be shifted north by tile_size
        north_tile = tile.north_neighbour()
        north_sw_x, north_sw_y = north_tile.south_west_corner()
        self.assertEqual(north_sw_x, tile_sw_x)
        self.assertEqual(north_sw_y, tile_sw_y + tile_size)

        # West neighbour should be shifted west by tile_size
        west_tile = tile.west_neighbour()
        west_sw_x, west_sw_y = west_tile.south_west_corner()
        self.assertEqual(west_sw_x, tile_sw_x - tile_size)
        self.assertEqual(west_sw_y, tile_sw_y)

        # South neighbour should be shifted south by tile_size
        south_tile = tile.south_neighbour()
        south_sw_x, south_sw_y = south_tile.south_west_corner()
        self.assertEqual(south_sw_x, tile_sw_x)
        self.assertEqual(south_sw_y, tile_sw_y - tile_size)

    def test_neighbour_level_preservation(self):
        """Test that neighbours are always at the same level."""
        for level in range(1, 10):
            tile = PackedTileId.from_tile_index(0, level)
            self.assertEqual(tile.north_neighbour().level(), level)
            self.assertEqual(tile.south_neighbour().level(), level)
            self.assertEqual(tile.east_neighbour().level(), level)
            self.assertEqual(tile.west_neighbour().level(), level)

    # ===== Level 15 Signed Int32 Tests =====

    def test_level15_signed_values(self):
        """Level 15 tiles should return negative values per NDS.Live standard."""
        # Morton 0 - minimum level 15 value
        tile = PackedTileId.from_tile_index(0, 15)
        self.assertEqual(tile.level(), 15)
        self.assertEqual(tile.morton_number(), 0)
        self.assertLess(tile.value, 0, "Level 15 tiles must have negative values")
        self.assertEqual(tile.value, -2147483648, "Level 15 morton 0 should be -2^31")

    def test_level15_max_morton(self):
        """Maximum morton for level 15 should give value -1."""
        max_morton = (1 << 31) - 1  # 2147483647
        tile = PackedTileId.from_tile_index(max_morton, 15)
        self.assertEqual(tile.value, -1, "Level 15 max morton should give value -1")
        self.assertEqual(tile.morton_number(), max_morton)
        self.assertEqual(tile.level(), 15)

    def test_constructor_accepts_negative_level15(self):
        """Constructor should accept negative values for level 15."""
        # Signed representation (negative)
        tile_signed = PackedTileId(-2147483648)
        self.assertEqual(tile_signed.level(), 15)
        self.assertEqual(tile_signed.morton_number(), 0)
        self.assertEqual(tile_signed.value, -2147483648)

        # Unsigned representation (positive, same bit pattern)
        tile_unsigned = PackedTileId(2147483648)
        self.assertEqual(tile_unsigned.level(), 15)
        self.assertEqual(tile_unsigned.morton_number(), 0)
        self.assertEqual(tile_unsigned.value, -2147483648, "Should return signed value")

        # Both should be equivalent
        self.assertEqual(tile_signed.value, tile_unsigned.value)
        self.assertEqual(tile_signed._value, tile_unsigned._value)

    def test_level15_roundtrip(self):
        """Test creating level 15 tiles from signed values and getting correct morton."""
        test_cases = [
            (0, -2147483648),  # Morton 0
            (1, -2147483647),  # Morton 1
            (1000000, -2146483648),  # Mid-range morton
            (100000000, -2047483648),  # Larger morton
            ((1 << 31) - 1, -1),  # Max morton
        ]

        for morton, expected_value in test_cases:
            with self.subTest(morton=morton, expected_value=expected_value):
                # Create from morton
                tile1 = PackedTileId.from_tile_index(morton, 15)
                self.assertEqual(tile1.value, expected_value)
                self.assertEqual(tile1.level(), 15)
                self.assertEqual(tile1.morton_number(), morton)

                # Create from signed value
                tile2 = PackedTileId(expected_value)
                self.assertEqual(tile2.morton_number(), morton)
                self.assertEqual(tile2.level(), 15)
                self.assertEqual(tile2.value, expected_value)

                # Both should be equivalent
                self.assertEqual(tile1.value, tile2.value)
                self.assertEqual(tile1._value, tile2._value)

    def test_levels_0_to_14_positive(self):
        """Levels 0-14 should always have positive values."""
        for level in range(0, 15):
            with self.subTest(level=level):
                # Test with morton 0
                tile = PackedTileId.from_tile_index(0, level)
                self.assertGreaterEqual(tile.value, 0, f"Level {level} should be positive")
                self.assertEqual(tile.level(), level)

                # Test with max morton for this level (if reasonable size)
                if level <= 10:  # Keep test fast for lower levels
                    max_morton = (1 << (2 * level + 1)) - 1
                    tile_max = PackedTileId.from_tile_index(max_morton, level)
                    self.assertGreaterEqual(
                        tile_max.value, 0, f"Level {level} max morton should be positive"
                    )

    def test_level15_neighbors(self):
        """Neighbor functions should work correctly with level 15 negative values."""
        # Test with a mid-range morton number
        tile = PackedTileId.from_tile_index(100, 15)
        self.assertLess(tile.value, 0, "Level 15 tile should be negative")

        # All neighbors should also be level 15 with negative values
        north = tile.north_neighbour()
        self.assertEqual(north.level(), 15)
        self.assertLess(north.value, 0, "Level 15 neighbor should be negative")

        south = tile.south_neighbour()
        self.assertEqual(south.level(), 15)
        self.assertLess(south.value, 0, "Level 15 neighbor should be negative")

        east = tile.east_neighbour()
        self.assertEqual(east.level(), 15)
        self.assertLess(east.value, 0, "Level 15 neighbor should be negative")

        west = tile.west_neighbour()
        self.assertEqual(west.level(), 15)
        self.assertLess(west.value, 0, "Level 15 neighbor should be negative")

        # Test reversibility
        self.assertEqual(tile, north.south_neighbour())
        self.assertEqual(tile, south.north_neighbour())
        self.assertEqual(tile, east.west_neighbour())
        self.assertEqual(tile, west.east_neighbour())

    def test_relative_neighbour(self):
        """Relative neighbour supports one-step and multi-step wrapped offsets."""
        tile = PackedTileId.from_tile_xy(0, 0, 1)
        self.assertEqual(tile.neighbour(1, 0), tile.east_neighbour())
        self.assertEqual(tile.neighbour(0, 1), tile.north_neighbour())
        self.assertEqual(tile.neighbour(-1, -1), PackedTileId.from_tile_xy(3, 1, 1))
        self.assertEqual(tile.neighbour(4, 2), tile)
        self.assertEqual(tile.neighbor(4, 2), tile.neighbour(4, 2))

    def test_level15_validation_accepts_negative(self):
        """Validation should accept negative values for level 15."""
        # Should not raise for valid level 15 values
        tile1 = PackedTileId(-2147483648)  # Min level 15
        self.assertEqual(tile1.level(), 15)

        tile2 = PackedTileId(-1)  # Max level 15
        self.assertEqual(tile2.level(), 15)

        tile3 = PackedTileId(-1000000000)  # Mid-range level 15
        self.assertEqual(tile3.level(), 15)

    def test_level15_comparison_operators(self):
        """Test that comparison operators work correctly with level 15 negative values."""
        tile1 = PackedTileId.from_tile_index(0, 15)  # value = -2147483648
        tile2 = PackedTileId.from_tile_index(1, 15)  # value = -2147483647
        tile3 = PackedTileId.from_tile_index(0, 15)  # value = -2147483648 (same as tile1)

        # Equality
        self.assertEqual(tile1, tile3)
        self.assertNotEqual(tile1, tile2)

        # Less than (should compare unsigned internally)
        self.assertLess(tile1, tile2)  # morton 0 < morton 1

    def test_comparison_with_foreign_type(self):
        """__eq__/__ne__ return NotImplemented for non-PackedTileId operands."""
        tile = PackedTileId.from_tile_index(0, 13)
        self.assertNotEqual(tile, 123)
        self.assertNotEqual(tile, "not a tile")
        self.assertNotEqual(tile, object())
        # The dunders themselves signal NotImplemented.
        self.assertIs(tile.__eq__(123), NotImplemented)
        self.assertIs(tile.__ne__(123), NotImplemented)

    def test_level15_int_conversion(self):
        """Test that __int__ returns signed value for level 15."""
        tile = PackedTileId.from_tile_index(0, 15)
        self.assertEqual(int(tile), -2147483648)
        self.assertLess(int(tile), 0)

    def test_level15_print_with_neighbors(self):
        """Test that print_with_neighbors works with level 15 negative values."""
        tile = PackedTileId.from_tile_index(0, 15)
        # Should not raise, will print to stdout
        try:
            tile.print_with_neighbors()
        except Exception as e:
            self.fail(f"print_with_neighbors failed for level 15: {e}")


class TestPackedTileIdLevel1Neighbors(unittest.TestCase):
    """Visual tests for level 1 neighbor wrapping behavior."""

    def test_tile_0_north(self):
        """Test north neighbor of tile 0 (0-00, northwest)."""
        print_level1_grid(current_morton=0, neighbor_morton=2, direction="NORTH")
        tile = PackedTileId.from_tile_index(0, 1)
        north = tile.north_neighbour()
        self.assertEqual(north.morton_number(), 2, "North of 0-00 should wrap to 0-10")

    def test_tile_0_south(self):
        """Test south neighbor of tile 0 (0-00)."""
        print_level1_grid(current_morton=0, neighbor_morton=2, direction="SOUTH")
        tile = PackedTileId.from_tile_index(0, 1)
        south = tile.south_neighbour()
        self.assertEqual(south.morton_number(), 2, "South of 0-00 should be 0-10")

    def test_tile_0_east(self):
        """Test east neighbor of tile 0 (0-00)."""
        print_level1_grid(current_morton=0, neighbor_morton=1, direction="EAST")
        tile = PackedTileId.from_tile_index(0, 1)
        east = tile.east_neighbour()
        self.assertEqual(east.morton_number(), 1, "East of 0-00 should be 0-01")

    def test_tile_0_west(self):
        """Test west neighbor of tile 0 (0-00)."""
        print_level1_grid(current_morton=0, neighbor_morton=5, direction="WEST")
        tile = PackedTileId.from_tile_index(0, 1)
        west = tile.west_neighbour()
        self.assertEqual(west.morton_number(), 5, "West of 0-00 should wrap to 1-01 (X=3)")

    def test_tile_1_east(self):
        """Test east neighbor of tile 1 (0-01), wraps to other hemisphere."""
        print_level1_grid(current_morton=1, neighbor_morton=4, direction="EAST")
        tile = PackedTileId.from_tile_index(1, 1)
        east = tile.east_neighbour()
        self.assertEqual(east.morton_number(), 4, "East of 0-01 should wrap to 1-00")

    def test_tile_4_west(self):
        """Test west neighbor of tile 4 (1-00), wraps to other hemisphere."""
        print_level1_grid(current_morton=4, neighbor_morton=1, direction="WEST")
        tile = PackedTileId.from_tile_index(4, 1)
        west = tile.west_neighbour()
        self.assertEqual(west.morton_number(), 1, "West of 1-00 should wrap to 0-01")


class TestMortonCode(unittest.TestCase):
    def test_basic_coordinate_conversion(self):
        """Test basic coordinate conversion roundtrip"""
        x, y = 132787847, 572604061
        morton = MortonCode.from_nds_coordinates(x, y)
        x_back, y_back = morton.to_nds_coordinates()
        self.assertEqual(x, x_back)
        self.assertEqual(y, y_back)

    def test_boundary_values(self):
        """Test boundary values for coordinates"""
        test_cases = [
            (0, 0),  # Origin
            ((1 << 31), (1 << 30)),  # Maximum values wrap to minimum
            (-(1 << 31), -(1 << 30)),  # Minimum values
            ((1 << 31) - 1, (1 << 30) - 1),  # Just below maximum
            (-(1 << 31) + 1, -(1 << 30) + 1),  # Just above minimum
        ]

        # Special case: maximum values should wrap to minimum values
        morton = MortonCode.from_nds_coordinates(1 << 31, 1 << 30)
        x_back, y_back = morton.to_nds_coordinates()
        self.assertEqual(x_back, -(1 << 31))  # Should wrap to minimum x
        self.assertEqual(y_back, -(1 << 30))  # Should wrap to minimum y

        # Test other boundary cases
        for x, y in test_cases[1:]:  # Skip the first case as we tested it above
            with self.subTest(x=x, y=y):
                morton = MortonCode.from_nds_coordinates(x, y)
                x_back, y_back = morton.to_nds_coordinates()
                # For maximum values, we expect them to wrap to minimum values
                if x == (1 << 31):
                    self.assertEqual(x_back, -(1 << 31))
                else:
                    self.assertEqual(x_back, x)
                if y == (1 << 30):
                    self.assertEqual(y_back, -(1 << 30))
                else:
                    self.assertEqual(y_back, y)

    def test_coordinate_wrapping(self):
        """Test coordinate wrapping behavior"""
        # Test values that should wrap around
        x_over = (1 << 32) + 100  # Should wrap to 100
        y_over = (1 << 31) + 50  # Should wrap to 50

        morton = MortonCode.from_nds_coordinates(x_over, y_over)
        x_back, y_back = morton.to_nds_coordinates()

        self.assertEqual(100, x_back)
        self.assertEqual(50, y_back)

    def test_bit_interleaving(self):
        """Test specific bit patterns to verify interleaving"""
        # Test with power of 2 values to check bit interleaving
        test_cases = [
            (1, 1),  # 0b1, 0b1
            (2, 2),  # 0b10, 0b10
            (4, 4),  # 0b100, 0b100
            (8, 8),  # 0b1000, 0b1000
        ]

        for x, y in test_cases:
            with self.subTest(x=x, y=y):
                morton = MortonCode.from_nds_coordinates(x, y)
                x_back, y_back = morton.to_nds_coordinates()
                self.assertEqual(x, x_back)
                self.assertEqual(y, y_back)

    def test_63rd_bit_masking(self):
        """Test that the 63rd bit is always masked off"""
        # Create coordinates that would set the 63rd bit if not masked
        x_max = (1 << 31) - 1
        y_max = (1 << 30) - 1

        morton = MortonCode.from_nds_coordinates(x_max, y_max)
        # Verify the 63rd bit is not set
        self.assertEqual(morton.value() & (1 << 63), 0)

    def test_value_method(self):
        """Test the value() method matches the C++ API"""
        morton = MortonCode(12345)
        self.assertEqual(morton.value(), 12345)

        # Test that values are properly masked to 64 bits
        morton_large = MortonCode(1 << 65)  # Should be masked
        self.assertLess(morton_large.value(), 1 << 64)


class TestBoundingBoxToTileIds(unittest.TestCase):
    def test_specific_bounding_box(self):
        """Test that the specified bounding box returns the correct tile ID."""
        # Given bounding box in NDS coordinates
        sw_x = 132644864  # southwest longitude
        sw_y = 572522496  # southwest latitude
        ne_x = 132907007  # northeast longitude
        ne_y = 572784639  # northeast latitude
        level = 13

        # Expected tile ID
        expected_tile_id = 545379780

        # Get tile IDs for the bounding box
        tile_ids = get_tile_ids_for_bounding_box(sw_x, sw_y, ne_x, ne_y, level)

        # Check that the expected tile ID is in the result
        tile_values = [tile.value for tile in tile_ids]
        self.assertIn(
            expected_tile_id,
            tile_values,
            f"Expected tile ID {expected_tile_id} not found in {tile_values}",
        )

        # Verify the bounding box is contained within a single tile at level 13
        self.assertEqual(
            len(tile_ids), 1, f"Expected 1 tile at level {level}, but got {len(tile_ids)}"
        )

    def test_bounding_box_multiple_tiles(self):
        """Test bounding box that spans multiple tiles."""
        # Create a bounding box that spans 2x2 tiles
        tile_size = 1 << (31 - 13)  # Size of a level 13 tile

        # Start at tile boundary
        sw_x = 0
        sw_y = 0
        # End just inside the neighboring tiles
        ne_x = tile_size + 1
        ne_y = tile_size + 1

        tile_ids = get_tile_ids_for_bounding_box(sw_x, sw_y, ne_x, ne_y, 13)

        # Should get exactly 4 tiles (2x2)
        self.assertEqual(len(tile_ids), 4)

    def test_single_point_bounding_box(self):
        """Test bounding box with same SW and NE corners."""
        x = 132644864
        y = 572522496
        level = 13

        tile_ids = get_tile_ids_for_bounding_box(x, y, x, y, level)

        # Should get exactly 1 tile
        self.assertEqual(len(tile_ids), 1)

    def test_negative_coordinates(self):
        """Test bounding box with negative coordinates."""
        sw_x = -132644864
        sw_y = -572522496
        ne_x = -132644864 + 100000
        ne_y = -572522496 + 100000
        level = 10

        tile_ids = get_tile_ids_for_bounding_box(sw_x, sw_y, ne_x, ne_y, level)

        # Should get at least one tile
        self.assertGreaterEqual(len(tile_ids), 1)

        # Verify all tiles have valid IDs
        for tile in tile_ids:
            self.assertGreater(tile.value, 0)
            self.assertEqual(tile.level(), level)

    def test_ground_truth_verification(self):
        """Test with known ground truth data."""
        # Given bounding box and expected results
        sw_x = -209157330
        sw_y = 174937580
        ne_x = -208540811
        ne_y = 175239411
        level = 13

        # Expected tile IDs from ground truth
        expected_tile_ids = {626579086, 626579087, 626579098, 626579120, 626579109, 626579108}

        # Get tile IDs for the bounding box
        tile_ids = get_tile_ids_for_bounding_box(sw_x, sw_y, ne_x, ne_y, level)

        # Should get exactly 6 tiles
        self.assertEqual(len(tile_ids), 6)

        # Verify all expected tiles are found
        found_ids = {tile.value for tile in tile_ids}
        self.assertEqual(found_ids, expected_tile_ids)


class TestBoundingBoxFromTileIds(unittest.TestCase):
    """Test bounding_box_from_tile_ids function."""

    def test_single_tile_property(self):
        """Test one-tile property: bbox from one tile covers only that tile."""
        # Use a real tile ID from test fixtures
        tile_id = PackedTileId(545554681)
        level = tile_id.level()

        # Get bounding box from this single tile
        sw_x, sw_y, ne_x, ne_y = bounding_box_from_tile_ids([tile_id])

        # Verify SW corner matches tile's SW corner (should be exact)
        tile_sw_x, tile_sw_y = tile_id.south_west_corner()
        self.assertEqual(sw_x, tile_sw_x)
        self.assertEqual(sw_y, tile_sw_y)

        # NE corner will be adjusted (tile.NE - 1) to be inclusive for get_tile_ids_for_bounding_box
        # So we don't check exact NE match, but verify the one-tile property instead

        # Verify inverse property: get_tile_ids_for_bounding_box returns only this tile
        result_tiles = get_tile_ids_for_bounding_box(sw_x, sw_y, ne_x, ne_y, level)
        self.assertEqual(
            len(result_tiles),
            1,
            f"Expected 1 tile, got {len(result_tiles)}: {[t.value for t in result_tiles]}",
        )
        self.assertEqual(result_tiles[0].value, tile_id.value)

    def test_multiple_adjacent_tiles(self):
        """Test bbox covers multiple adjacent tiles."""
        # 2x2 grid of level 13 tiles from test fixture (Munich region)
        tile_ids = [
            PackedTileId(545554681),
            PackedTileId(545554683),
            PackedTileId(545554684),
            PackedTileId(545554686),
        ]

        sw_x, sw_y, ne_x, ne_y = bounding_box_from_tile_ids(tile_ids)

        # Result should cover all input tiles
        result_tiles = get_tile_ids_for_bounding_box(sw_x, sw_y, ne_x, ne_y, 13)
        result_ids = {t.value for t in result_tiles}
        input_ids = {t.value for t in tile_ids}

        # All input tiles should be in result
        self.assertTrue(input_ids.issubset(result_ids))

    def test_accepts_integer_tile_ids(self):
        """Test function accepts both PackedTileId objects and integers."""
        tile_ids_int = [545554681, 545554683]
        tile_ids_obj = [PackedTileId(545554681), PackedTileId(545554683)]

        bbox1 = bounding_box_from_tile_ids(tile_ids_int)
        bbox2 = bounding_box_from_tile_ids(tile_ids_obj)

        self.assertEqual(bbox1, bbox2)

    def test_mixed_tile_id_types(self):
        """Test function accepts mixed list of integers and PackedTileId objects."""
        tile_ids_mixed = [545554681, PackedTileId(545554683)]

        # Should not raise an error
        bbox = bounding_box_from_tile_ids(tile_ids_mixed)
        self.assertEqual(len(bbox), 4)  # Should return 4-tuple

    def test_empty_list_raises_error(self):
        """Test empty list raises ValueError."""
        with self.assertRaises(ValueError) as context:
            bounding_box_from_tile_ids([])

        self.assertIn("cannot be empty", str(context.exception))

    def test_invalid_type_raises_error(self):
        """Test invalid tile ID type raises TypeError."""
        with self.assertRaises(TypeError):
            bounding_box_from_tile_ids(["not a tile id"])

    def test_distant_tiles_different_regions(self):
        """Test bbox correctly covers tiles from different regions."""
        # Munich tile and Berlin tile (from test fixture)
        tile_ids = [
            PackedTileId(545554681),  # Munich region
            PackedTileId(545666600),  # Berlin region
        ]

        sw_x, sw_y, ne_x, ne_y = bounding_box_from_tile_ids(tile_ids)

        # Result should cover both tiles
        result_tiles = get_tile_ids_for_bounding_box(sw_x, sw_y, ne_x, ne_y, 13)
        result_ids = {t.value for t in result_tiles}

        self.assertIn(545554681, result_ids)
        self.assertIn(545666600, result_ids)

    def test_returns_tuple_of_four_integers(self):
        """Test function returns tuple of 4 integers."""
        tile_id = PackedTileId(545554681)
        result = bounding_box_from_tile_ids([tile_id])

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 4)
        for coord in result:
            self.assertIsInstance(coord, int)


class TestNdsBoundingBox(unittest.TestCase):
    """Tests for NdsBoundingBox class."""

    def test_basic_constructor(self):
        """Test basic NdsBoundingBox construction."""
        bbox = NdsBoundingBox(100, 200, 300, 400)

        self.assertEqual(bbox.min_x, 100)
        self.assertEqual(bbox.min_y, 200)
        self.assertEqual(bbox.max_x, 300)
        self.assertEqual(bbox.max_y, 400)

    def test_from_tile(self):
        """Test creating bbox from a tile ID."""
        tile = PackedTileId.from_tile_index(4, 2)
        bbox = NdsBoundingBox.from_tile(tile)

        # Verify bbox matches tile corners
        sw_x, sw_y = tile.south_west_corner()
        ne_x, ne_y = tile.north_east_corner()

        self.assertEqual(bbox.min_x, sw_x)
        self.assertEqual(bbox.min_y, sw_y)
        self.assertEqual(bbox.max_x, ne_x)
        self.assertEqual(bbox.max_y, ne_y)

    def test_from_tile_with_int(self):
        """Test creating bbox from an integer tile ID."""
        tile_value = PackedTileId.from_tile_index(4, 2).value
        bbox = NdsBoundingBox.from_tile(tile_value)

        tile = PackedTileId(tile_value)
        sw_x, sw_y = tile.south_west_corner()
        ne_x, ne_y = tile.north_east_corner()

        self.assertEqual(bbox.min_x, sw_x)
        self.assertEqual(bbox.min_y, sw_y)
        self.assertEqual(bbox.max_x, ne_x)
        self.assertEqual(bbox.max_y, ne_y)

    def test_from_wgs84_corners(self):
        """Test creating bbox from WGS84 corner coordinates."""
        # Create WGS84 corners for a bbox around Berlin
        sw = Wgs84(13.0, 52.0)  # SW corner
        ne = Wgs84(14.0, 53.0)  # NE corner

        bbox = NdsBoundingBox.from_wgs84_corners(sw, ne)

        # Convert back to verify
        sw_back = Wgs84.from_nds_coordinates(bbox.min_x, bbox.min_y)
        ne_back = Wgs84.from_nds_coordinates(bbox.max_x, bbox.max_y)

        self.assertAlmostEqual(sw_back.x, 13.0, places=4)
        self.assertAlmostEqual(sw_back.y, 52.0, places=4)
        self.assertAlmostEqual(ne_back.x, 14.0, places=4)
        self.assertAlmostEqual(ne_back.y, 53.0, places=4)

    def test_intersects_overlapping(self):
        """Test intersects with overlapping boxes."""
        bbox1 = NdsBoundingBox(0, 0, 100, 100)
        bbox2 = NdsBoundingBox(50, 50, 150, 150)

        self.assertTrue(bbox1.intersects(bbox2))
        self.assertTrue(bbox2.intersects(bbox1))

    def test_intersects_non_overlapping(self):
        """Test intersects with non-overlapping boxes."""
        bbox1 = NdsBoundingBox(0, 0, 100, 100)
        bbox2 = NdsBoundingBox(200, 200, 300, 300)

        self.assertFalse(bbox1.intersects(bbox2))
        self.assertFalse(bbox2.intersects(bbox1))

    def test_intersects_touching_edges(self):
        """Test intersects with touching edges (touching = intersecting)."""
        bbox1 = NdsBoundingBox(0, 0, 100, 100)
        bbox2 = NdsBoundingBox(100, 0, 200, 100)

        # Touching at edge counts as intersecting
        self.assertTrue(bbox1.intersects(bbox2))

    def test_intersects_one_inside_other(self):
        """Test intersects when one box is inside another."""
        outer = NdsBoundingBox(0, 0, 100, 100)
        inner = NdsBoundingBox(25, 25, 75, 75)

        self.assertTrue(outer.intersects(inner))
        self.assertTrue(inner.intersects(outer))

    def test_contains_inner_box(self):
        """Test contains with inner box."""
        outer = NdsBoundingBox(0, 0, 100, 100)
        inner = NdsBoundingBox(25, 25, 75, 75)

        self.assertTrue(outer.contains(inner))
        self.assertFalse(inner.contains(outer))

    def test_contains_same_box(self):
        """Test contains with same box."""
        bbox = NdsBoundingBox(0, 0, 100, 100)

        self.assertTrue(bbox.contains(bbox))

    def test_contains_partially_overlapping(self):
        """Test contains with partially overlapping boxes."""
        bbox1 = NdsBoundingBox(0, 0, 100, 100)
        bbox2 = NdsBoundingBox(50, 50, 150, 150)

        self.assertFalse(bbox1.contains(bbox2))
        self.assertFalse(bbox2.contains(bbox1))

    def test_tile_intersection_check(self):
        """Test using bbox for tile intersection checking."""
        # Create a bbox from WGS84 coordinates
        sw = Wgs84(13.3, 52.4)
        ne = Wgs84(13.5, 52.6)
        query_bbox = NdsBoundingBox.from_wgs84_corners(sw, ne)

        # Create a tile at level 13 containing the area
        wgs_center = Wgs84(13.4, 52.5)
        cx, cy = wgs_center.to_nds_coordinates()
        morton = MortonCode.from_nds_coordinates(cx, cy)
        tile = PackedTileId.from_morton_and_level(morton, 13)
        tile_bbox = NdsBoundingBox.from_tile(tile)

        # The tile should intersect with the query bbox
        self.assertTrue(query_bbox.intersects(tile_bbox))
        self.assertTrue(tile_bbox.intersects(query_bbox))


class TestDistanceConversions(unittest.TestCase):
    """Tests for Wgs84 distance conversion utilities."""

    def test_degrees_to_meters_at_equator(self):
        """At equator (latitude 0), both longitude and latitude should have same meters per degree."""
        METERS_PER_DEGREE = 111320.0

        lon_meters, lat_meters = Wgs84.degrees_to_meters(1.0, 1.0, 0.0)

        self.assertAlmostEqual(lon_meters, METERS_PER_DEGREE, delta=0.1)
        self.assertAlmostEqual(lat_meters, METERS_PER_DEGREE, delta=0.1)

    def test_degrees_to_meters_at_different_latitudes(self):
        """Test degree to meter conversion at various latitudes."""
        METERS_PER_DEGREE = 111320.0

        # At 60° latitude, longitude distance should be ~half of equatorial
        lon_meters60, lat_meters60 = Wgs84.degrees_to_meters(1.0, 1.0, 60.0)

        self.assertAlmostEqual(lon_meters60, METERS_PER_DEGREE * 0.5, delta=1.0)
        self.assertAlmostEqual(lat_meters60, METERS_PER_DEGREE, delta=0.1)

        # At poles (90°), longitude distance should be ~0
        lon_meters90, lat_meters90 = Wgs84.degrees_to_meters(1.0, 1.0, 90.0)

        self.assertAlmostEqual(lon_meters90, 0.0, delta=1.0)
        self.assertAlmostEqual(lat_meters90, METERS_PER_DEGREE, delta=0.1)

    def test_nds_distance_to_meters_conversion(self):
        """Test NDS distance to meters conversion."""
        # Test with a known NDS distance
        # At equator, half of NDS X range should cover half the earth's longitude
        HALF_NDS_X = 1 << 31  # Half of NDS X range
        HALF_NDS_Y = 1 << 30  # Half of NDS Y range

        lon_meters, lat_meters = Wgs84.nds_distance_to_meters(HALF_NDS_X, HALF_NDS_Y, 0.0)

        # Half the X range = 180° longitude at equator ≈ 20,037 km
        self.assertAlmostEqual(lon_meters, 20037500.0, delta=1000.0)

        # Half the Y range = 90° latitude ≈ 10,018 km
        self.assertAlmostEqual(lat_meters, 10018750.0, delta=1000.0)

    def test_packedtileid_dimensions_in_meters(self):
        """Test PackedTileId.dimensions_in_meters() method."""
        # Test with tiles at a mid-latitude (45°) where dimensions are reasonable
        wgs45 = Wgs84(lon=0.0, lat=45.0)
        x45, y45 = wgs45.to_nds_coordinates()
        morton45 = MortonCode.from_nds_coordinates(x45, y45)

        # Test level 5 tile (reasonable size)
        tile5 = PackedTileId.from_morton_and_level(morton45, 5)
        width5, height5 = tile5.dimensions_in_meters()

        # Dimensions should be positive and reasonable
        self.assertGreater(width5, 0.0)
        self.assertGreater(height5, 0.0)
        self.assertLess(width5, 10000000.0)  # Less than 10,000 km
        self.assertLess(height5, 10000000.0)

        # Test level 6 tile (smaller than level 5)
        tile6 = PackedTileId.from_morton_and_level(morton45, 6)
        width6, height6 = tile6.dimensions_in_meters()

        # Higher level should have smaller dimensions
        self.assertLess(width6, width5)
        self.assertLess(height6, height5)

        # Each level increase divides tile size by 2
        # Note: Width varies slightly due to different tile center latitudes
        self.assertAlmostEqual(width6, width5 / 2.0, delta=10000.0)
        self.assertAlmostEqual(height6, height5 / 2.0, delta=1000.0)

    def test_tile_dimensions_vary_by_latitude(self):
        """Test that tile dimensions vary by latitude as expected."""
        # Create tiles at different latitudes at level 5
        # Tile near equator
        wgsEquator = Wgs84(lon=0.0, lat=0.0)
        xEq, yEq = wgsEquator.to_nds_coordinates()
        mortonEq = MortonCode.from_nds_coordinates(xEq, yEq)
        tileEquator = PackedTileId.from_morton_and_level(mortonEq, 5)
        widthEq, heightEq = tileEquator.dimensions_in_meters()

        # Tile at higher latitude (~60°)
        wgs60 = Wgs84(lon=0.0, lat=60.0)
        x60, y60 = wgs60.to_nds_coordinates()
        morton60 = MortonCode.from_nds_coordinates(x60, y60)
        tile60 = PackedTileId.from_morton_and_level(morton60, 5)
        width60, height60 = tile60.dimensions_in_meters()

        # Width should decrease with latitude (cos effect)
        self.assertLess(width60, widthEq)

        # Height should remain approximately the same
        self.assertAlmostEqual(height60, heightEq, delta=100.0)


if __name__ == "__main__":
    unittest.main()
