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
