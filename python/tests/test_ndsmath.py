import unittest
from ndsmath import Wgs84, PackedTileId, MortonCode

class TestWgs84(unittest.TestCase):
    def test_initialization(self):
        point = Wgs84(lon=10.0, lat=20.0, alt=30.0)
        self.assertEqual(point.x, 10.0)
        self.assertEqual(point.y, 20.0)
        self.assertEqual(point.z, 30.0)

    def test_normalization(self):
        point = Wgs84(lon=190.0, lat=100.0)
        self.assertLess(point.x, 180.0)
        self.assertLess(point.y, 90.0)

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
    def test_level_extraction(self):
        tile = PackedTileId(value=545379780)
        self.assertEqual(tile.level(), 13)

class TestMortonCode(unittest.TestCase):
    def test_coordinate_conversion(self):
        x, y = 132787847, 572604061
        morton = MortonCode.from_nds_coordinates(x, y)
        x_back, y_back = morton.to_nds_coordinates()
        self.assertEqual(x, x_back)
        self.assertEqual(y, y_back)

if __name__ == '__main__':
    unittest.main()
