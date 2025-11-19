import unittest
import math  # Add math import
from ndslive.math import Wgs84, PackedTileId, MortonCode
from ndslive.math.tileid import get_tile_ids_for_bounding_box, bounding_box_from_tile_ids

class TestWgs84(unittest.TestCase):
    def test_initialization(self):
        point = Wgs84(lon=10.0, lat=20.0, alt=30.0)
        self.assertEqual(point.x, 10.0)
        self.assertEqual(point.y, 20.0)
        self.assertEqual(point.z, 30.0)

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
        self.assertAlmostEqual(Wgs84(-180.0, 0).x, -180.0, places=12) # Should stay -180
        self.assertAlmostEqual(Wgs84(180.0, 0).x, 180.0 - Wgs84.LON_NDS_DELTA, places=12) # Should become ~180 - delta
        self.assertAlmostEqual(Wgs84(180.0 - Wgs84.LON_NDS_DELTA / 2, 0).x, 180.0 - Wgs84.LON_NDS_DELTA, places=12) # Close to 180
        # Wrapping
        self.assertAlmostEqual(Wgs84(190.0, 0).x, -170.0, places=12) # 190 -> -170
        self.assertAlmostEqual(Wgs84(-190.0, 0).x, 170.0, places=12) # -190 -> 170
        self.assertAlmostEqual(Wgs84(370.0, 0).x, 10.0, places=12) # 370 -> 10
        self.assertAlmostEqual(Wgs84(-370.0, 0).x, -10.0, places=12) # -370 -> -10
        self.assertAlmostEqual(Wgs84(540.0, 0).x, 180.0 - Wgs84.LON_NDS_DELTA, places=12) # 540 -> 180 -> ~180 - delta
        self.assertAlmostEqual(Wgs84(-540.0, 0).x, -180.0, places=12) # -540 -> -180

        # Test latitude normalization
        # Within range
        self.assertAlmostEqual(Wgs84(0, 80.0).y, 80.0, places=12)
        self.assertAlmostEqual(Wgs84(0, -80.0).y, -80.0, places=12)
        # Boundaries and clamping
        self.assertAlmostEqual(Wgs84(0, -90.0).y, -90.0, places=12) # Min lat
        self.assertAlmostEqual(Wgs84(0, 90.0).y, 90.0 - Wgs84.LAT_NDS_DELTA, places=12) # Max lat becomes 90 - delta
        self.assertAlmostEqual(Wgs84(0, 90.0 - Wgs84.LAT_NDS_DELTA / 2).y, 90.0 - Wgs84.LAT_NDS_DELTA, places=12) # Close to 90
        self.assertAlmostEqual(Wgs84(0, 100.0).y, 90.0 - Wgs84.LAT_NDS_DELTA, places=12) # Above 90 - delta gets clamped
        self.assertAlmostEqual(Wgs84(0, -100.0).y, -90.0, places=12) # Below -90 gets clamped

    def test_distance_calculation(self):
        point1 = Wgs84(0, 0)
        point2 = Wgs84(1, 1)
        distance = point1.distance_to(point2)
        self.assertGreater(distance, 0)

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
    def test_validity(self):
        """Port of 'PackedTileId is valid' test"""
        tile = PackedTileId()
        self.assertEqual(tile.value, 0)

    def test_levels(self):
        """Port of 'PackedTileId levels' test"""
        for level in range(1, 16):
            # Create tile-id from level 1 to 15 and check level
            tile = PackedTileId(value=(1 << (level + 16)))
            self.assertEqual(tile.level(), level)

    def test_tile_number(self):
        """Port of 'PackedTileId tile number' test"""
        TILE_LEVEL_13 = 13
        LEVEL13_TILE_LEN_NDS_UNITS = 1 << (32-(TILE_LEVEL_13+1))
        size = LEVEL13_TILE_LEN_NDS_UNITS

        test_data = [
            (1 * size//2, 1 * size//2, TILE_LEVEL_13, 0),
            (3 * size//2, 1 * size//2, TILE_LEVEL_13, 1),
            (1 * size//2, 3 * size//2, TILE_LEVEL_13, 2),
            (3 * size//2, 3 * size//2, TILE_LEVEL_13, 3)
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
        y_over = (1 << 31) + 50   # Should wrap to 50

        morton = MortonCode.from_nds_coordinates(x_over, y_over)
        x_back, y_back = morton.to_nds_coordinates()

        self.assertEqual(100, x_back)
        self.assertEqual(50, y_back)

    def test_bit_interleaving(self):
        """Test specific bit patterns to verify interleaving"""
        # Test with power of 2 values to check bit interleaving
        test_cases = [
            (1, 1),      # 0b1, 0b1
            (2, 2),      # 0b10, 0b10
            (4, 4),      # 0b100, 0b100
            (8, 8),      # 0b1000, 0b1000
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
        self.assertIn(expected_tile_id, tile_values, 
                      f"Expected tile ID {expected_tile_id} not found in {tile_values}")
        
        # Verify the bounding box is contained within a single tile at level 13
        self.assertEqual(len(tile_ids), 1, 
                         f"Expected 1 tile at level {level}, but got {len(tile_ids)}")
        
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
        expected_tile_ids = {
            626579086, 626579087, 626579098, 626579120, 626579109, 626579108
        }
        
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
        self.assertEqual(len(result_tiles), 1, f"Expected 1 tile, got {len(result_tiles)}: {[t.value for t in result_tiles]}")
        self.assertEqual(result_tiles[0].value, tile_id.value)

    def test_multiple_adjacent_tiles(self):
        """Test bbox covers multiple adjacent tiles."""
        # 2x2 grid of level 13 tiles from test fixture (Munich region)
        tile_ids = [
            PackedTileId(545554681),
            PackedTileId(545554683),
            PackedTileId(545554684),
            PackedTileId(545554686)
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
            PackedTileId(545666600)   # Berlin region
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


if __name__ == '__main__':
    unittest.main()
