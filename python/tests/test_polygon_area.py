# SPDX-License-Identifier: BSD-3-Clause
"""Shared area vectors and nonfinite boundary cases."""

import json
import math
import random
import unittest
from fractions import Fraction
from pathlib import Path

from ndslive.math import (
    PolygonAreaRelation,
    Vec2,
    classify_polygon_rectangle,
    polygon_areas_intersect,
    valid_polygon_area,
)


class PolygonAreaTest(unittest.TestCase):
    """Validate all vector cases in the Python generator reference."""

    def test_vectors(self):
        data = json.loads(
            (Path(__file__).parents[2] / "test-vectors/parity_vectors.json").read_text()
        )
        for row in data["polygon_area"]:
            exterior = [Vec2(*p) for p in row["exterior"]]
            holes = [[Vec2(*p) for p in ring] for ring in row["holes"]]
            self.assertEqual(valid_polygon_area(exterior, holes), row["valid"], row["name"])
            for other in row["intersections"]:
                self.assertEqual(
                    polygon_areas_intersect(
                        exterior,
                        holes,
                        [Vec2(*p) for p in other["exterior"]],
                        [[Vec2(*p) for p in h] for h in other["holes"]],
                    ),
                    other["intersects"],
                    row["name"],
                )
                if row["name"] == "inside-hole" and other["holes"]:
                    self.assertFalse(other["intersects"])
                if row["name"] == "contact-hole" and other["holes"]:
                    self.assertTrue(other["intersects"])
            for query in row["queries"]:
                self.assertEqual(
                    int(
                        classify_polygon_rectangle(
                            exterior, holes, Vec2(*query["minimum"]), Vec2(*query["maximum"])
                        )
                    ),
                    query["relation"],
                    row["name"],
                )

    def test_nonfinite(self):
        self.assertFalse(valid_polygon_area([Vec2(0, 0), Vec2(1, 0), Vec2(math.nan, 1)]))
        exterior = [Vec2(0, 0), Vec2(1, 0), Vec2(0, 1)]
        self.assertEqual(
            classify_polygon_rectangle(exterior, [], Vec2(math.inf, 0), Vec2(1, 1)),
            PolygonAreaRelation.OUTSIDE,
        )

    def test_orientation_against_exact_rationals(self):
        """An independent integer/rational oracle exercises ambiguous turns."""
        from ndslive.math.polygon_area import _cross

        rng = random.Random(23)
        step = 180 / 2**31
        for _ in range(2000):
            raw = [rng.randrange(-(2**30), 2**30) for _ in range(6)]
            a, b, c = [Vec2(raw[i] * step, raw[i + 1] * step) for i in (0, 2, 4)]
            exact = (Fraction(b.x) - Fraction(a.x)) * (Fraction(c.y) - Fraction(a.y)) - (
                Fraction(b.y) - Fraction(a.y)
            ) * (Fraction(c.x) - Fraction(a.x))
            actual = _cross(a, b, c)
            self.assertEqual((actual > 0) - (actual < 0), (exact > 0) - (exact < 0))
        a = Vec2(0, 0)
        for power in range(27, 32):
            b = Vec2((2**power - 1) * step, (2**power - 2) * step)
            c = Vec2(2**power * step, (2**power - 1) * step)
            self.assertGreater(_cross(a, b, c), 0)
