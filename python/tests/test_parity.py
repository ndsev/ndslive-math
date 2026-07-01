# SPDX-License-Identifier: BSD-3-Clause
"""Validate the Python implementation against the shared golden parity vectors.

The same ``test-vectors/parity_vectors.json`` is consumed by every language
port, so this test keeps the reference implementation honest against the
contract it itself produced (and catches accidental drift if the vectors are
regenerated from changed code without updating tests).
"""

import json
import math
import os
import unittest

from ndslive.math import (
    MortonCode,
    NdsBoundingBox,
    PackedTileId,
    Wgs84,
    bounding_box_from_tile_ids,
    get_tile_ids_for_bounding_box,
)

_HERE = os.path.dirname(os.path.abspath(__file__))


def _find_vectors():
    override = os.environ.get("PARITY_VECTORS")
    if override:
        return override
    d = _HERE
    for _ in range(6):
        cand = os.path.join(d, "test-vectors", "parity_vectors.json")
        if os.path.exists(cand):
            return cand
        d = os.path.dirname(d)
    raise FileNotFoundError(
        "parity_vectors.json not found; set PARITY_VECTORS or run from the repo"
    )


with open(_find_vectors()) as _f:
    VECTORS = json.load(_f)

TOL = VECTORS["_meta"]["float_tolerance"]


class TestParityVectors(unittest.TestCase):
    def assertClose(self, a, b, msg=""):
        self.assertTrue(
            math.isclose(a, b, rel_tol=0, abs_tol=TOL) or math.isclose(a, b, rel_tol=1e-9),
            f"{msg}: {a} != {b}",
        )

    def test_wgs84_to_nds(self):
        for r in VECTORS["wgs84_to_nds"]:
            w = Wgs84(lon=r["lon"], lat=r["lat"])
            self.assertClose(w.x, r["normalized_lon"], "normalized_lon")
            self.assertClose(w.y, r["normalized_lat"], "normalized_lat")
            self.assertEqual(list(w.to_nds_coordinates()), [r["nds_x"], r["nds_y"]])

    def test_nds_to_wgs84(self):
        for r in VECTORS["nds_to_wgs84"]:
            w = Wgs84.from_nds_coordinates(r["x"], r["y"])
            self.assertClose(w.x, r["lon"], "lon")
            self.assertClose(w.y, r["lat"], "lat")

    def test_morton(self):
        for r in VECTORS["morton"]:
            m = MortonCode.from_nds_coordinates(r["x"], r["y"])
            self.assertEqual(m.value(), int(r["morton"]))
            self.assertEqual(list(m.to_nds_coordinates()), [r["decoded_x"], r["decoded_y"]])

    def test_packed_tile_from_index(self):
        for r in VECTORS["packed_tile_from_index"]:
            t = PackedTileId.from_tile_index(r["morton_number"], r["level"])
            self.assertEqual(t.value, r["value"])
            self.assertEqual(t.level(), r["computed_level"])
            self.assertEqual(t.morton_number(), r["computed_morton_number"])
            self.assertEqual(t.x(), r["grid_x"])
            self.assertEqual(t.y(), r["grid_y"])
            self.assertEqual(t.size(), r["size"])
            self.assertEqual(list(t.south_west_corner()), r["sw"])
            self.assertEqual(list(t.north_east_corner()), r["ne"])
            self.assertEqual(list(t.center()), r["center"])
            self.assertEqual(PackedTileId.from_value(r["value"]).value, r["value"])
            self.assertEqual(
                PackedTileId.from_tile_xy(r["grid_x"], r["grid_y"], r["level"]).value,
                r["value"],
            )

    def test_tile_neighbours(self):
        for r in VECTORS["tile_neighbours"]:
            t = PackedTileId.from_tile_index(r["morton_number"], r["level"])
            self.assertEqual(t.west_neighbour().value, r["west"])
            self.assertEqual(t.east_neighbour().value, r["east"])
            self.assertEqual(t.south_neighbour().value, r["south"])
            self.assertEqual(t.north_neighbour().value, r["north"])

    def test_from_morton_and_level(self):
        for r in VECTORS["from_morton_and_level"]:
            m = MortonCode.from_nds_coordinates(r["x"], r["y"])
            t = PackedTileId.from_morton_and_level(m, r["level"])
            self.assertEqual(t.value, r["value"])
            self.assertEqual(t.level(), r["computed_level"])
            self.assertEqual(t.morton_number(), r["computed_morton_number"])
            from_nds = PackedTileId.from_nds_coordinates(r["x"], r["y"], r["level"])
            self.assertEqual(from_nds.value, r["value"])

    def test_packed_tile_from_wgs84(self):
        for r in VECTORS["packed_tile_from_wgs84"]:
            t = PackedTileId.from_wgs84(r["lon"], r["lat"], r["level"])
            self.assertEqual(t.value, r["value"])
            self.assertEqual(t.morton_number(), r["computed_morton_number"])
            self.assertEqual(t.x(), r["grid_x"])
            self.assertEqual(t.y(), r["grid_y"])

    def test_tiles_for_bbox(self):
        for r in VECTORS["tiles_for_bbox"]:
            tiles = get_tile_ids_for_bounding_box(
                r["sw_x"], r["sw_y"], r["ne_x"], r["ne_y"], r["level"]
            )
            self.assertEqual([t.value for t in tiles], r["tile_values"])

    def test_bbox_from_tiles(self):
        for r in VECTORS["bbox_from_tiles"]:
            tiles = [PackedTileId(v) for v in r["tile_values"]]
            self.assertEqual(list(bounding_box_from_tile_ids(tiles)), r["result"])

    def test_nds_bbox_ops(self):
        for r in VECTORS["nds_bbox_ops"]:
            a = NdsBoundingBox(*r["a"])
            b = NdsBoundingBox(*r["b"])
            self.assertEqual(a.intersects(b), r["intersects"])
            self.assertEqual(a.contains(b), r["a_contains_b"])

    def test_nds_bbox_from_wgs84(self):
        for r in VECTORS["nds_bbox_from_wgs84"]:
            bbox = NdsBoundingBox.from_wgs84_corners(
                Wgs84(lon=r["sw"][0], lat=r["sw"][1]), Wgs84(lon=r["ne"][0], lat=r["ne"][1])
            )
            self.assertEqual(bbox.min_x, r["min_x"])
            self.assertEqual(bbox.min_y, r["min_y"])
            self.assertEqual(bbox.max_x, r["max_x"])
            self.assertEqual(bbox.max_y, r["max_y"])

    def test_distance_bearing(self):
        for r in VECTORS["distance_bearing"]:
            a = Wgs84(lon=r["a"][0], lat=r["a"][1])
            b = Wgs84(lon=r["b"][0], lat=r["b"][1])
            self.assertClose(a.distance_to(b), r["distance_m"], "distance")
            self.assertClose(a.bearing_from(b), r["bearing_rad"], "bearing")

    def test_nds_distance_to_meters(self):
        for r in VECTORS["nds_distance_to_meters"]:
            w, h = Wgs84.nds_distance_to_meters(r["nds_x"], r["nds_y"], r["at_latitude"])
            self.assertClose(w, r["width_m"], "width")
            self.assertClose(h, r["height_m"], "height")


if __name__ == "__main__":
    unittest.main()
