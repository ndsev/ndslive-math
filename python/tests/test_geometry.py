# SPDX-License-Identifier: BSD-3-Clause
"""Unit tests for the geometry layer (Polygon, Wgs84Polygon, Wgs84Aabb,
PolygonTriangulation), ported from the C++ reference in ``cpp/``.

Expected values are taken from the language-neutral port specification, which
in turn was computed from the C++ semantics (power-of-two NDS deltas:
``LON_NDS_DELTA_POW2 = 360 / 2^32`` and ``LON_MAX = 179.99999991618097``).
"""

import math
import unittest

from ndslive.math import (
    Orientation,
    PackedTileId,
    Polygon,
    PolygonTriangulation,
    PolygonType,
    Vec2,
    Wgs84,
    Wgs84Aabb,
    Wgs84Polygon,
)

# Mirror the parity-vector float tolerance for degree-valued comparisons.
TOL = 1e-6


def _shoelace_area(verts: list[Wgs84]) -> float:
    n = len(verts)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += verts[i].x * verts[j].y - verts[i].y * verts[j].x
    return abs(area) / 2.0


class TestPolygon(unittest.TestCase):
    def test_default_construction(self):
        p = Polygon()
        self.assertEqual(p.type(), PolygonType.UNKNOWN)
        self.assertFalse(p.is_valid())  # empty → invalid

    def test_set_type_and_add_vertices(self):
        p = Polygon()
        p.set_type(PolygonType.SIMPLE_POLYGON)
        self.assertEqual(p.type(), PolygonType.SIMPLE_POLYGON)

        p.add_vertex(Wgs84(0, 0))
        p.add_vertices([Wgs84(1, 0), Wgs84(0, 1)])
        self.assertTrue(p.is_valid())  # non-empty → valid
        self.assertEqual(len(p.vertices()), 3)

        # Subscript access (and mutation).
        self.assertAlmostEqual(p[0].longitude(), 0.0, places=12)
        self.assertAlmostEqual(p[1].longitude(), 1.0, places=12)
        p.vertices().append(Wgs84(2, 2))
        self.assertEqual(len(p.vertices()), 4)

    def test_base_is_valid_threshold(self):
        # Base Polygon: >= 1 vertex.
        self.assertFalse(Polygon(PolygonType.SIMPLE_POLYGON).is_valid())
        self.assertTrue(Polygon(PolygonType.SIMPLE_POLYGON, [Wgs84(0, 0)]).is_valid())

    def test_orientation_ccw(self):
        p = Polygon(PolygonType.SIMPLE_POLYGON, [Wgs84(0, 0), Wgs84(1, 0), Wgs84(0, 1)])
        self.assertEqual(p.orientation(), Orientation.COUNTERCLOCKWISE)

    def test_orientation_cw(self):
        p = Polygon(PolygonType.SIMPLE_POLYGON, [Wgs84(0, 0), Wgs84(0, 1), Wgs84(1, 0)])
        self.assertEqual(p.orientation(), Orientation.CLOCKWISE)

    def test_orientation_collinear(self):
        p = Polygon(PolygonType.SIMPLE_POLYGON, [Wgs84(0, 0), Wgs84(1, 1), Wgs84(2, 2)])
        self.assertEqual(p.orientation(), Orientation.INVALID_ORIENTATION)

    def test_orientation_unsupported_type(self):
        p = Polygon(PolygonType.TRIANGLE_STRIP, [Wgs84(0, 0), Wgs84(1, 0), Wgs84(0, 1)])
        self.assertEqual(p.orientation(), Orientation.INVALID_ORIENTATION)

    def test_orientation_triangle_list_single(self):
        p = Polygon(PolygonType.TRIANGLE_LIST, [Wgs84(0, 0), Wgs84(1, 0), Wgs84(0, 1)])
        self.assertEqual(p.orientation(), Orientation.COUNTERCLOCKWISE)

    def test_orientation_multi_triangle_list_invalid(self):
        # A TRIANGLE_LIST with != 3 vertices is unsupported.
        p = Polygon(
            PolygonType.TRIANGLE_LIST,
            [Wgs84(0, 0), Wgs84(4, 0), Wgs84(4, 4), Wgs84(0, 4), Wgs84(0, 0), Wgs84(4, 0)],
        )
        self.assertEqual(p.orientation(), Orientation.INVALID_ORIENTATION)

    def test_orientation_quad(self):
        p = Polygon(
            PolygonType.SIMPLE_POLYGON,
            [Wgs84(0, 0), Wgs84(4, 0), Wgs84(4, 4), Wgs84(0, 4)],
        )
        self.assertEqual(p.orientation(), Orientation.COUNTERCLOCKWISE)

    def test_enum_integer_values(self):
        self.assertEqual(int(Orientation.CLOCKWISE), -1)
        self.assertEqual(int(Orientation.INVALID_ORIENTATION), 0)
        self.assertEqual(int(Orientation.COUNTERCLOCKWISE), 1)
        self.assertEqual(int(PolygonType.SIMPLE_POLYGON), 0)
        self.assertEqual(int(PolygonType.TRIANGLE_STRIP), 1)
        self.assertEqual(int(PolygonType.TRIANGLE_FAN), 2)
        self.assertEqual(int(PolygonType.TRIANGLE_LIST), 3)
        self.assertEqual(int(PolygonType.UNKNOWN), 4)


class TestWgs84Polygon(unittest.TestCase):
    def test_default_is_simple_polygon(self):
        empty = Wgs84Polygon()
        self.assertEqual(empty.type(), PolygonType.SIMPLE_POLYGON)
        self.assertFalse(empty.is_valid())  # < 3 vertices

    def test_is_valid_threshold(self):
        self.assertFalse(Wgs84Polygon(vertices=[Wgs84(0, 0), Wgs84(1, 0)]).is_valid())
        self.assertTrue(Wgs84Polygon(vertices=[Wgs84(0, 0), Wgs84(1, 0), Wgs84(0, 1)]).is_valid())

    def test_equality(self):
        tri = Wgs84Polygon(vertices=[Wgs84(0, 0), Wgs84(4, 0), Wgs84(0, 4)])
        same = Wgs84Polygon(vertices=[Wgs84(0, 0), Wgs84(4, 0), Wgs84(0, 4)])
        diff_vert = Wgs84Polygon(vertices=[Wgs84(0, 0), Wgs84(4, 0), Wgs84(1, 4)])
        quad = Wgs84Polygon(vertices=[Wgs84(0, 0), Wgs84(4, 0), Wgs84(4, 4), Wgs84(0, 4)])
        self.assertEqual(tri, same)
        self.assertNotEqual(tri, diff_vert)  # same size, different vertex
        self.assertNotEqual(tri, quad)  # different size

    def test_aabb_triangle(self):
        bb = Wgs84Polygon(vertices=[Wgs84(0, 0), Wgs84(4, 0), Wgs84(0, 4)]).aa_bb()
        self.assertAlmostEqual(bb.sw().longitude(), 0.0, delta=TOL)
        self.assertAlmostEqual(bb.sw().latitude(), 0.0, delta=TOL)
        self.assertAlmostEqual(bb.size().x, 4.0, delta=TOL)
        self.assertAlmostEqual(bb.size().y, 4.0, delta=TOL)
        self.assertTrue(bb.valid())

    def test_aabb_quad(self):
        bb = Wgs84Polygon(
            vertices=[Wgs84(13, 52), Wgs84(14, 52), Wgs84(14, 53), Wgs84(13, 53)]
        ).aa_bb()
        self.assertAlmostEqual(bb.sw().longitude(), 13.0, delta=TOL)
        self.assertAlmostEqual(bb.sw().latitude(), 52.0, delta=TOL)
        self.assertAlmostEqual(bb.size().x, 1.0, delta=TOL)
        self.assertAlmostEqual(bb.size().y, 1.0, delta=TOL)

    def test_aabb_invalid_polygon_is_default(self):
        bb = Wgs84Polygon(vertices=[Wgs84(0, 0), Wgs84(1, 0)]).aa_bb()
        self.assertAlmostEqual(bb.sw().longitude(), 0.0, delta=TOL)
        self.assertAlmostEqual(bb.sw().latitude(), 0.0, delta=TOL)
        self.assertAlmostEqual(bb.size().x, 0.0, delta=TOL)
        self.assertAlmostEqual(bb.size().y, 0.0, delta=TOL)
        self.assertTrue(bb.valid())

    def test_median_symmetric_triangle(self):
        # Symmetric: the lon/lat swap is invisible.
        m = Wgs84Polygon(vertices=[Wgs84(0, 0), Wgs84(4, 0), Wgs84(0, 4)]).median()
        self.assertAlmostEqual(m.longitude(), 4.0 / 3.0, places=12)
        self.assertAlmostEqual(m.latitude(), 4.0 / 3.0, places=12)

    def test_median_symmetric_quad(self):
        m = Wgs84Polygon(vertices=[Wgs84(0, 0), Wgs84(4, 0), Wgs84(4, 4), Wgs84(0, 4)]).median()
        self.assertAlmostEqual(m.longitude(), 2.0, places=12)
        self.assertAlmostEqual(m.latitude(), 2.0, places=12)

    def test_median_asymmetric(self):
        # Centroid of an asymmetric polygon: mean_lon = 10, mean_lat = 20.
        m = Wgs84Polygon(vertices=[Wgs84(0, 0), Wgs84(30, 0), Wgs84(0, 60)]).median()
        self.assertAlmostEqual(m.longitude(), 10.0, places=12)
        self.assertAlmostEqual(m.latitude(), 20.0, places=12)

    def test_earth_wrapping_poly_structure(self):
        earth = Wgs84Polygon.earth_wrapping_poly()
        self.assertEqual(len(earth.vertices()), 4)

    def test_collides_with_earth_wrapper(self):
        tri = Wgs84Polygon(vertices=[Wgs84(0, 0), Wgs84(4, 0), Wgs84(0, 4)])
        earth = Wgs84Polygon.earth_wrapping_poly()
        self.assertTrue(earth.collides_with(tri))
        self.assertTrue(tri.collides_with(earth))

    def test_collides_with_overlap(self):
        tri = Wgs84Polygon(vertices=[Wgs84(0, 0), Wgs84(4, 0), Wgs84(0, 4)])
        overlap = Wgs84Polygon(vertices=[Wgs84(1, 1), Wgs84(5, 1), Wgs84(1, 5)])
        self.assertTrue(tri.collides_with(overlap))
        self.assertTrue(overlap.collides_with(tri))

    def test_collides_with_disjoint(self):
        tri = Wgs84Polygon(vertices=[Wgs84(0, 0), Wgs84(4, 0), Wgs84(0, 4)])
        apart = Wgs84Polygon(vertices=[Wgs84(20, 20), Wgs84(24, 20), Wgs84(20, 24)])
        self.assertFalse(tri.collides_with(apart))
        self.assertFalse(apart.collides_with(tri))


class TestWgs84Aabb(unittest.TestCase):
    def setUp(self):
        self.box = Wgs84Aabb(Wgs84(0, 10), Vec2(20, 10))

    def test_construction_and_corners(self):
        box = self.box
        self.assertTrue(box.valid())
        self.assertAlmostEqual(box.sw().longitude(), 0.0, delta=TOL)
        self.assertAlmostEqual(box.sw().latitude(), 10.0, delta=TOL)
        self.assertAlmostEqual(box.ne().longitude(), 20.0, delta=TOL)
        self.assertAlmostEqual(box.ne().latitude(), 20.0, delta=TOL)
        self.assertAlmostEqual(box.nw().longitude(), 0.0, delta=TOL)
        self.assertAlmostEqual(box.nw().latitude(), 20.0, delta=TOL)
        self.assertAlmostEqual(box.se().longitude(), 20.0, delta=TOL)
        self.assertAlmostEqual(box.se().latitude(), 10.0, delta=TOL)
        self.assertAlmostEqual(box.center().longitude(), 10.0, delta=TOL)
        self.assertAlmostEqual(box.center().latitude(), 15.0, delta=TOL)
        self.assertAlmostEqual(box.size().x, 20.0, delta=TOL)
        self.assertAlmostEqual(box.size().y, 10.0, delta=TOL)

    def test_vertices_order(self):
        verts = self.box.vertices()
        self.assertEqual(len(verts), 4)
        expected = [(0, 10), (20, 10), (20, 20), (0, 20)]
        for v, (ex, ey) in zip(verts, expected, strict=True):
            self.assertAlmostEqual(v.longitude(), ex, delta=TOL)
            self.assertAlmostEqual(v.latitude(), ey, delta=TOL)

    def test_excess_height_clamp(self):
        # 90 - 85 - 10 = -5 → size.y reduced by 5 → 5.0.
        clamp = Wgs84Aabb(Wgs84(0, 85), Vec2(10, 10))
        self.assertAlmostEqual(clamp.size().x, 10.0, delta=TOL)
        self.assertAlmostEqual(clamp.size().y, 5.0, delta=TOL)
        self.assertTrue(clamp.valid())
        # NE latitude approaches +90 (clamped to LAT_MAX by Wgs84 normalization).
        self.assertAlmostEqual(clamp.ne().longitude(), 10.0, delta=TOL)
        self.assertAlmostEqual(clamp.ne().latitude(), 90.0, delta=TOL)

    def test_default_aabb(self):
        d = Wgs84Aabb()
        self.assertAlmostEqual(d.sw().longitude(), 0.0, delta=TOL)
        self.assertAlmostEqual(d.sw().latitude(), 0.0, delta=TOL)
        self.assertAlmostEqual(d.size().x, 0.0, delta=TOL)
        self.assertAlmostEqual(d.size().y, 0.0, delta=TOL)
        self.assertTrue(d.valid())

    def test_invalid_box_does_not_clamp(self):
        # Negative size → invalid → size stored unmodified (no clamp).
        bad = Wgs84Aabb(Wgs84(0, 85), Vec2(-1, 10))
        self.assertFalse(bad.valid())
        self.assertAlmostEqual(bad.size().y, 10.0, delta=TOL)

    def test_from_tile_path_a(self):
        tbox = Wgs84Aabb.from_tile(PackedTileId.from_tile_index(0, 10))
        self.assertTrue(tbox.valid())
        self.assertAlmostEqual(tbox.sw().longitude(), 0.0, delta=TOL)
        self.assertAlmostEqual(tbox.sw().latitude(), 0.0, delta=TOL)
        self.assertAlmostEqual(tbox.size().x, 0.17578125, delta=TOL)
        self.assertAlmostEqual(tbox.size().y, 0.17578125, delta=TOL)

    def test_from_center_and_tile_limit(self):
        cbox = Wgs84Aabb.from_center_and_tile_limit(Wgs84(0, 0), 16, 10)
        self.assertGreater(cbox.size().x, 0.0)
        self.assertGreater(cbox.size().y, 0.0)
        self.assertTrue(cbox.valid())

    def test_contains(self):
        box = self.box
        self.assertTrue(box.contains(Wgs84(5, 15)))
        self.assertFalse(box.contains(Wgs84(50, 50)))
        self.assertTrue(box.contains(Wgs84(0, 10)))  # SW corner, inclusive
        self.assertTrue(box.contains(Wgs84(20, 20)))  # NE corner, inclusive

    def test_num_tile_ids(self):
        box = self.box
        for lv in (0, 1, 2, 3):
            self.assertEqual(box.num_tile_ids(lv), 1)
        self.assertEqual(box.num_tile_ids(4), 2)
        self.assertEqual(box.num_tile_ids(5), 8)
        self.assertEqual(box.num_tile_ids(8), 435)

    def test_tile_level(self):
        self.assertEqual(self.box.tile_level(8), 5)
        self.assertEqual(self.box.tile_level(2), 4)

    def test_tile_level_falls_back_to_15(self):
        tiny = Wgs84Aabb(Wgs84(0, 0), Vec2(0.0001, 0.0001))
        self.assertEqual(tiny.tile_level(1000), 15)

    def test_intersects_overlap(self):
        over = Wgs84Aabb(Wgs84(10, 15), Vec2(20, 10))
        self.assertTrue(self.box.intersects(over))
        self.assertTrue(over.intersects(self.box))

    def test_intersects_disjoint(self):
        far = Wgs84Aabb(Wgs84(100, 60), Vec2(5, 5))
        self.assertFalse(self.box.intersects(far))
        self.assertFalse(far.intersects(self.box))  # symmetric, no recursion

    def test_intersects_cross_shaped(self):
        # Neither holds the other's corner, yet they overlap on x∈[8,10], y∈[14,16].
        wide = Wgs84Aabb(Wgs84(-5, 14), Vec2(40, 2))
        tall = Wgs84Aabb(Wgs84(8, 0), Vec2(2, 40))
        self.assertTrue(wide.intersects(tall))
        self.assertTrue(tall.intersects(wide))

    def test_contains_anti_meridian_false(self):
        self.assertFalse(self.box.contains_anti_meridian())

    def test_contains_anti_meridian_true(self):
        am = Wgs84Aabb(Wgs84(175, 0), Vec2(10, 5))
        self.assertTrue(am.contains_anti_meridian())

    def test_split_over_anti_meridian(self):
        am = Wgs84Aabb(Wgs84(175, 0), Vec2(10, 5))
        split = am.split_over_anti_meridian()
        self.assertIsNotNone(split)
        assert split is not None  # for type checker
        left, right = split
        self.assertAlmostEqual(left.sw().longitude(), 175.0, delta=TOL)
        self.assertAlmostEqual(left.sw().latitude(), 0.0, delta=TOL)
        self.assertAlmostEqual(left.size().x, 4.999999916180968, delta=TOL)
        self.assertAlmostEqual(left.size().y, 5.0, delta=TOL)
        self.assertAlmostEqual(right.sw().longitude(), -180.0, delta=TOL)
        self.assertAlmostEqual(right.sw().latitude(), 0.0, delta=TOL)
        self.assertAlmostEqual(right.size().x, 5.000000083819032, delta=TOL)
        self.assertAlmostEqual(right.size().y, 5.0, delta=TOL)
        self.assertGreater(left.size().x, 0.0)
        self.assertGreater(right.size().x, 0.0)

    def test_split_over_anti_meridian_none_when_not_crossing(self):
        self.assertIsNone(self.box.split_over_anti_meridian())

    def test_avg_mercator_stretch_is_finite(self):
        # Transcendental; only finiteness is asserted (not parity-canonical).
        self.assertTrue(math.isfinite(self.box.avg_mercator_stretch()))


class TestPolygonTriangulation(unittest.TestCase):
    def setUp(self):
        self.tri = PolygonTriangulation()

    def test_too_few_vertices(self):
        too_few = Wgs84Polygon(vertices=[Wgs84(0, 0), Wgs84(1, 0)])
        result = self.tri.triangulate_by_ear_clipping(too_few)
        self.assertEqual(result.type(), PolygonType.UNKNOWN)
        self.assertEqual(len(result.vertices()), 0)

    def test_wrong_type(self):
        not_simple = Wgs84Polygon(
            PolygonType.TRIANGLE_LIST, [Wgs84(0, 0), Wgs84(4, 0), Wgs84(0, 4)]
        )
        result = self.tri.triangulate_by_ear_clipping(not_simple)
        self.assertEqual(result.type(), PolygonType.UNKNOWN)

    def test_triangle_unchanged(self):
        triangle = Wgs84Polygon(vertices=[Wgs84(0, 0), Wgs84(4, 0), Wgs84(0, 4)])
        result = self.tri.triangulate_by_ear_clipping(triangle)
        self.assertEqual(result.type(), PolygonType.TRIANGLE_LIST)
        self.assertEqual(len(result.vertices()), 3)
        # Vertices copied unchanged, in order.
        for got, exp in zip(result.vertices(), triangle.vertices(), strict=True):
            self.assertAlmostEqual(got.longitude(), exp.longitude(), delta=TOL)
            self.assertAlmostEqual(got.latitude(), exp.latitude(), delta=TOL)

    def test_convex_quad(self):
        quad = Wgs84Polygon(vertices=[Wgs84(0, 0), Wgs84(4, 0), Wgs84(4, 4), Wgs84(0, 4)])
        result = self.tri.triangulate_by_ear_clipping(quad)
        self.assertEqual(result.type(), PolygonType.TRIANGLE_LIST)
        self.assertEqual(len(result.vertices()), 6)  # 3 * (4 - 2)
        self._assert_triangles_tile(quad, result)

    def test_concave_with_reflex_vertex(self):
        concave = Wgs84Polygon(
            vertices=[
                Wgs84(0, 0),
                Wgs84(4, 0),
                Wgs84(4, 4),
                Wgs84(2, 2),  # reflex vertex
                Wgs84(0, 4),
            ]
        )
        result = self.tri.triangulate_by_ear_clipping(concave)
        self.assertEqual(result.type(), PolygonType.TRIANGLE_LIST)
        self.assertEqual(len(result.vertices()), 9)  # 3 * (5 - 2)
        self._assert_triangles_tile(concave, result)

    def _assert_triangles_tile(self, polygon: Wgs84Polygon, result: Wgs84Polygon) -> None:
        """The union of output triangles must cover the polygon area exactly."""
        verts = result.vertices()
        total = 0.0
        for k in range(0, len(verts), 3):
            total += _shoelace_area([verts[k], verts[k + 1], verts[k + 2]])
        self.assertAlmostEqual(total, _shoelace_area(polygon.vertices()), delta=TOL)


class TestVec2(unittest.TestCase):
    def test_arithmetic(self):
        a = Vec2(1.0, 2.0)
        b = Vec2(3.0, 4.0)
        self.assertEqual(a + b, Vec2(4.0, 6.0))
        self.assertEqual(b - a, Vec2(2.0, 2.0))
        self.assertEqual(a * 2.0, Vec2(2.0, 4.0))
        self.assertEqual(2.0 * a, Vec2(2.0, 4.0))

    def test_abs_and_not_normalized(self):
        # Vec2 is a raw extent: values beyond 360/180 and negatives survive.
        big = Vec2(720.0, -45.0)
        self.assertEqual(big.x, 720.0)
        self.assertEqual(big.y, -45.0)
        self.assertEqual(big.abs(), Vec2(720.0, 45.0))

    def test_iter_unpacking(self):
        x, y = Vec2(7.0, 8.0)
        self.assertEqual((x, y), (7.0, 8.0))


class TestWgs84GeometrySupport(unittest.TestCase):
    """Supporting methods/constants added to Wgs84 for the geometry layer."""

    def test_geometry_constants(self):
        self.assertAlmostEqual(Wgs84.LON_NDS_DELTA_POW2, 8.381903171539307e-08, places=20)
        self.assertAlmostEqual(Wgs84.LAT_NDS_DELTA_POW2, 8.381903171539307e-08, places=20)
        self.assertEqual(Wgs84.LON_MIN, -180.0)
        self.assertAlmostEqual(Wgs84.LON_MAX, 179.99999991618097, places=10)
        self.assertEqual(Wgs84.LAT_MIN, -90.0)
        # Distinct from the existing (2^32 - 1) deltas.
        self.assertNotEqual(Wgs84.LON_NDS_DELTA_POW2, Wgs84.LON_NDS_DELTA)

    def test_accessors(self):
        p = Wgs84(11.5, 48.1)
        self.assertEqual(p.longitude(), p.x)
        self.assertEqual(p.latitude(), p.y)
        self.assertEqual(p.dx(), p.x)
        self.assertEqual(p.dy(), p.y)

    def test_from_morton_code_scales_both_axes_by_pow2(self):
        from ndslive.math import MortonCode

        # from_morton_code uses 360/2^32 for BOTH axes (unlike
        # from_nds_coordinates, which uses 180/2^31 for latitude).
        x_nds, y_nds = 2097152, 2097152
        m = MortonCode.from_nds_coordinates(x_nds, y_nds)
        p = Wgs84.from_morton_code(m)
        scaling = 360.0 / (2**32)
        dx, dy = m.to_nds_coordinates()
        self.assertAlmostEqual(p.longitude(), dx * scaling, places=12)
        self.assertAlmostEqual(p.latitude(), dy * scaling, places=12)


if __name__ == "__main__":
    unittest.main()
