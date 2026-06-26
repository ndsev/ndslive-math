#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Generate the language-neutral parity vectors for ndslive-math.

These golden vectors are produced from the **Python reference implementation**
(the working-tree source under ``python/src``) and are consumed by the test
suite of every language port (C++, Java, JavaScript/TS, Go, Rust) so that all
implementations are guaranteed to agree bit-for-bit on integer results and to
within a tolerance on floating-point results.

Run from the repository root:

    PYTHONPATH=python/src python3 test-vectors/generate_vectors.py

This rewrites ``test-vectors/parity_vectors.json``. Commit the result. The JSON
is the contract; do not hand-edit it.
"""

import json
import os
import sys

# Import the reference implementation from the working tree (not any installed
# copy, which may be stale).
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "python", "src"))

from ndslive.math import (  # noqa: E402
    MortonCode,
    NdsBoundingBox,
    PackedTileId,
    Polygon,
    PolygonType,
    Vec2,
    Wgs84,
    Wgs84Aabb,
    Wgs84Polygon,
    bounding_box_from_tile_ids,
    get_tile_ids_for_bounding_box,
)

# ---------------------------------------------------------------------------
# Input fixtures
# ---------------------------------------------------------------------------

# (lon, lat) sample points: cities, origin, sign variants, near-boundaries.
WGS84_POINTS = [
    (0.0, 0.0),
    (13.404954, 52.520008),  # Berlin
    (11.585, 48.137),  # Munich
    (-122.4194, 37.7749),  # San Francisco
    (151.2093, -33.8688),  # Sydney
    (-43.1729, -22.9068),  # Rio de Janeiro
    (139.6917, 35.6895),  # Tokyo
    (-0.1276, 51.5072),  # London
    (179.9, 0.0),
    (-179.9, 0.0),
    (180.0, 90.0),  # exercises clamping/wrapping
    (-180.0, -90.0),
    (179.999999, 89.999999),
    (-0.000001, -0.000001),  # near-origin negatives (floor vs truncate)
    (360.5, 0.0),  # wrap > 360
    (-360.5, 0.0),
    (90.0, 45.0),
    (-90.0, -45.0),
]

# NDS integer coordinates: signed range exercises.
NDS_COORDS = [
    (0, 0),
    (1, 1),
    (-1, -1),
    (1000000, 500000),
    (-1000000, -500000),
    ((1 << 31) - 1, (1 << 30) - 1),
    (-(1 << 31), -(1 << 30)),
    (123456789, -98765432),
    (-2000000000, 1000000000),
]

# (x, y) for Morton round-trips (NDS coords, signed).
MORTON_COORDS = [
    (0, 0),
    (1, 0),
    (0, 1),
    (1, 1),
    (12345, 6789),
    (-12345, -6789),
    ((1 << 31) - 1, (1 << 30) - 1),
    (-(1 << 31), -(1 << 30)),
    (1000000000, -1000000000),
]

# (morton_number, level) for tile construction. morton must be <= 2^(2*level+1)-1.
TILE_INDEX = [
    (0, 0),
    (1, 0),
    (0, 1),
    (3, 1),
    (7, 1),
    (0, 2),
    (4, 2),
    (31, 2),
    (0, 13),
    (12345, 13),
    (0, 14),
    (1 << 20, 14),
    (0, 15),
    ((1 << 31) - 1, 15),
    (1234567, 15),
]

# (x_nds, y_nds, level) for from_morton_and_level (containing-tile lookup).
FROM_MORTON_LEVEL = [
    (0, 0, 0),
    (1000000, 500000, 5),
    (123456789, 98765432, 13),
    (-1000000, -500000, 10),
    ((1 << 31) - 1, (1 << 30) - 1, 15),
]

# (sw_x, sw_y, ne_x, ne_y, level) bounding boxes for tile enumeration.
TILES_FOR_BBOX = [
    (0, 0, (1 << 28), (1 << 28), 3),
    (1000000, 500000, 2000000, 1500000, 8),
    (0, 0, (1 << 31) - 1, (1 << 30) - 1, 1),
]

# ---------------------------------------------------------------------------
# Geometry-layer input fixtures (deterministic methods only)
# ---------------------------------------------------------------------------

# Wgs84Aabb cases as (name, sw_lon, sw_lat, size_x, size_y). These exercise the
# excess-height clamp, the anti-meridian split, the default/invalid boxes, and
# the tile-count helpers. Construction goes through the Wgs84Aabb constructor,
# which clamps height for valid boxes and leaves invalid boxes untouched.
AABB_CASES = [
    ("origin_box", 0.0, 0.0, 20.0, 10.0),
    ("offset_box", 0.0, 10.0, 20.0, 10.0),
    ("clamp_box", 0.0, 85.0, 10.0, 10.0),  # excess-height clamp: size.y -> 5
    ("anti_meridian_box", 175.0, 0.0, 10.0, 5.0),  # crosses +180
    ("wide_box", -5.0, 14.0, 40.0, 2.0),  # cross-shaped overlap partner
    ("tall_box", 8.0, 0.0, 2.0, 40.0),  # cross-shaped overlap partner
    ("invalid_neg_size", 0.0, 85.0, -1.0, 10.0),  # invalid: no clamp
    ("default_box", 0.0, 0.0, 0.0, 0.0),
    ("tiny_box", 0.0, 0.0, 0.0001, 0.0001),  # tile_level falls back to 15
]

# (name, x_nds, y_nds) sample points for Wgs84Aabb.contains, tested against
# every AABB case above. Includes inclusive-edge corners of origin_box.
AABB_CONTAINS_POINTS = [
    ("inside", 5.0, 5.0),
    ("sw_corner_origin", 0.0, 0.0),
    ("ne_corner_origin", 20.0, 10.0),
    ("far_outside", 50.0, 50.0),
    ("near_am", 178.0, 2.0),
]

# Index pairs (into AABB_CASES) for the pairwise intersects() matrix. We test
# all ordered pairs so symmetry is verified by the ports.
# (computed in main as a full cross product)

# Polygon orientation/validity cases: (name, polygon_type_int, vertices).
# vertices are raw (lon, lat) and are NOT normalized for orientation, but the
# Wgs84 constructor still normalizes; all sample coords are well inside range so
# the stored value equals the literal.
POLYGON_CASES = [
    ("ccw_triangle", 0, [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]),
    ("cw_triangle", 0, [(0.0, 0.0), (0.0, 1.0), (1.0, 0.0)]),
    ("collinear", 0, [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)]),
    ("ccw_quad", 0, [(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)]),
    ("triangle_list_single", 3, [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]),
    ("triangle_strip_unsupported", 1, [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]),
    ("triangle_list_multi", 3, [(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)]),
    ("single_vertex", 0, [(0.0, 0.0)]),
    ("two_vertices", 0, [(0.0, 0.0), (1.0, 0.0)]),
    ("empty", 0, []),
]

# Wgs84Polygon cases (always SIMPLE_POLYGON): (name, vertices).
WGS84_POLYGON_CASES = [
    ("triangle", [(0.0, 0.0), (4.0, 0.0), (0.0, 4.0)]),
    ("asymmetric_triangle", [(0.0, 0.0), (30.0, 0.0), (0.0, 60.0)]),
    ("quad", [(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)]),
    ("berlin_quad", [(13.0, 52.0), (14.0, 52.0), (14.0, 53.0), (13.0, 53.0)]),
    ("invalid_two_vertices", [(0.0, 0.0), (1.0, 0.0)]),
]

# Ordered pairs (index into WGS84_POLYGON_CASES) for collides_with, plus a
# couple of synthetic overlapping/disjoint triangles defined inline by name.
WGS84_POLYGON_COLLISION_PAIRS = [
    (
        "triangle",
        [(0.0, 0.0), (4.0, 0.0), (0.0, 4.0)],
        "overlap",
        [(1.0, 1.0), (5.0, 1.0), (1.0, 5.0)],
    ),
    (
        "triangle",
        [(0.0, 0.0), (4.0, 0.0), (0.0, 4.0)],
        "disjoint",
        [(20.0, 20.0), (24.0, 20.0), (20.0, 24.0)],
    ),
    (
        "triangle",
        [(0.0, 0.0), (4.0, 0.0), (0.0, 4.0)],
        "self",
        [(0.0, 0.0), (4.0, 0.0), (0.0, 4.0)],
    ),
    (
        "quad",
        [(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)],
        "shifted_quad",
        [(2.0, 2.0), (6.0, 2.0), (6.0, 6.0), (2.0, 6.0)],
    ),
]

# float comparison tolerance the ports should use for distance/bearing/meters
FLOAT_TOLERANCE = 1e-6


def main():
    data = {
        "_meta": {
            "description": "Golden parity vectors for ndslive-math, generated "
            "from the Python reference implementation.",
            "float_tolerance": FLOAT_TOLERANCE,
            "source": "python/src/ndslive/math",
        }
    }

    # 1. WGS84 -> NDS (with normalized lon/lat)
    rows = []
    for lon, lat in WGS84_POINTS:
        w = Wgs84(lon=lon, lat=lat)
        x_nds, y_nds = w.to_nds_coordinates()
        rows.append(
            {
                "lon": lon,
                "lat": lat,
                "normalized_lon": w.x,
                "normalized_lat": w.y,
                "nds_x": x_nds,
                "nds_y": y_nds,
            }
        )
    data["wgs84_to_nds"] = rows

    # 2. NDS -> WGS84
    rows = []
    for x, y in NDS_COORDS:
        w = Wgs84.from_nds_coordinates(x, y)
        rows.append({"x": x, "y": y, "lon": w.x, "lat": w.y})
    data["nds_to_wgs84"] = rows

    # 3. Morton encode/decode round-trip
    rows = []
    for x, y in MORTON_COORDS:
        m = MortonCode.from_nds_coordinates(x, y)
        dx, dy = m.to_nds_coordinates()
        rows.append(
            {
                "x": x,
                "y": y,
                "morton": str(m.value()),  # may exceed 2^53; transport as string
                "decoded_x": dx,
                "decoded_y": dy,
            }
        )
    data["morton"] = rows

    # 4. PackedTileId from tile index: value/level/morton/size/corners/center
    rows = []
    for morton_number, level in TILE_INDEX:
        t = PackedTileId.from_tile_index(morton_number, level)
        rows.append(
            {
                "morton_number": morton_number,
                "level": level,
                "value": t.value,
                "computed_level": t.level(),
                "computed_morton_number": t.morton_number(),
                "size": t.size(),
                "sw": list(t.south_west_corner()),
                "ne": list(t.north_east_corner()),
                "center": list(t.center()),
            }
        )
    data["packed_tile_from_index"] = rows

    # 5. Neighbours (report neighbour .value)
    rows = []
    for morton_number, level in TILE_INDEX:
        if level == 0:
            continue  # level 0 neighbour behaviour is degenerate; skip
        t = PackedTileId.from_tile_index(morton_number, level)
        rows.append(
            {
                "morton_number": morton_number,
                "level": level,
                "west": t.west_neighbour().value,
                "east": t.east_neighbour().value,
                "south": t.south_neighbour().value,
                "north": t.north_neighbour().value,
            }
        )
    data["tile_neighbours"] = rows

    # 6. from_morton_and_level (containing tile)
    rows = []
    for x, y, level in FROM_MORTON_LEVEL:
        m = MortonCode.from_nds_coordinates(x, y)
        t = PackedTileId.from_morton_and_level(m, level)
        rows.append(
            {
                "x": x,
                "y": y,
                "level": level,
                "value": t.value,
                "computed_level": t.level(),
                "computed_morton_number": t.morton_number(),
            }
        )
    data["from_morton_and_level"] = rows

    # 7. get_tile_ids_for_bounding_box
    rows = []
    for sw_x, sw_y, ne_x, ne_y, level in TILES_FOR_BBOX:
        tiles = get_tile_ids_for_bounding_box(sw_x, sw_y, ne_x, ne_y, level)
        rows.append(
            {
                "sw_x": sw_x,
                "sw_y": sw_y,
                "ne_x": ne_x,
                "ne_y": ne_y,
                "level": level,
                "tile_values": [t.value for t in tiles],
            }
        )
    data["tiles_for_bbox"] = rows

    # 8. bounding_box_from_tile_ids
    rows = []
    for morton_number, level in TILE_INDEX:
        if level == 0:
            continue
        t = PackedTileId.from_tile_index(morton_number, level)
        bbox = bounding_box_from_tile_ids([t])
        rows.append(
            {
                "tile_values": [t.value],
                "result": list(bbox),
            }
        )
    data["bbox_from_tiles"] = rows

    # 9. NdsBoundingBox operations
    rows = []
    boxes = [
        (0, 0, 100, 100),
        (50, 50, 150, 150),
        (200, 200, 300, 300),
        (10, 10, 20, 20),
    ]
    for ax, ay, axx, ayy in boxes:
        for bx, by, bxx, byy in boxes:
            a = NdsBoundingBox(ax, ay, axx, ayy)
            b = NdsBoundingBox(bx, by, bxx, byy)
            rows.append(
                {
                    "a": [ax, ay, axx, ayy],
                    "b": [bx, by, bxx, byy],
                    "intersects": a.intersects(b),
                    "a_contains_b": a.contains(b),
                }
            )
    data["nds_bbox_ops"] = rows

    # 10. NdsBoundingBox.from_wgs84_corners
    rows = []
    corner_pairs = [
        ((11.5, 48.1), (11.7, 48.2)),
        ((-1.0, -1.0), (1.0, 1.0)),
        ((13.0, 52.0), (14.0, 53.0)),
    ]
    for (sw_lon, sw_lat), (ne_lon, ne_lat) in corner_pairs:
        bbox = NdsBoundingBox.from_wgs84_corners(
            Wgs84(lon=sw_lon, lat=sw_lat), Wgs84(lon=ne_lon, lat=ne_lat)
        )
        rows.append(
            {
                "sw": [sw_lon, sw_lat],
                "ne": [ne_lon, ne_lat],
                "min_x": bbox.min_x,
                "min_y": bbox.min_y,
                "max_x": bbox.max_x,
                "max_y": bbox.max_y,
            }
        )
    data["nds_bbox_from_wgs84"] = rows

    # 11. Floating-point helpers (compare with FLOAT_TOLERANCE)
    rows = []
    pairs = [
        ((13.404954, 52.520008), (11.585, 48.137)),  # Berlin -> Munich
        ((0.0, 0.0), (0.0, 1.0)),
        ((-122.4194, 37.7749), (139.6917, 35.6895)),  # SF -> Tokyo
    ]
    for (lon1, lat1), (lon2, lat2) in pairs:
        a = Wgs84(lon=lon1, lat=lat1)
        b = Wgs84(lon=lon2, lat=lat2)
        rows.append(
            {
                "a": [lon1, lat1],
                "b": [lon2, lat2],
                "distance_m": a.distance_to(b),
                "bearing_rad": a.bearing_from(b),
            }
        )
    data["distance_bearing"] = rows

    rows = []
    for nds_x, nds_y, at_lat in [
        (1 << 20, 1 << 20, 0.0),
        (1 << 18, 1 << 18, 48.137),
        (1 << 22, 1 << 22, 60.0),
    ]:
        w_m, h_m = Wgs84.nds_distance_to_meters(nds_x, nds_y, at_lat)
        rows.append(
            {
                "nds_x": nds_x,
                "nds_y": nds_y,
                "at_latitude": at_lat,
                "width_m": w_m,
                "height_m": h_m,
            }
        )
    data["nds_distance_to_meters"] = rows

    # -----------------------------------------------------------------------
    # Geometry layer (deterministic methods only; PolygonTriangulation and the
    # transcendental avg_mercator_stretch are intentionally excluded).
    # -----------------------------------------------------------------------

    def _pt(w: Wgs84) -> list[float]:
        return [w.longitude(), w.latitude()]

    def _make_aabb(sw_lon, sw_lat, size_x, size_y) -> Wgs84Aabb:
        return Wgs84Aabb(Wgs84(sw_lon, sw_lat), Vec2(size_x, size_y))

    # 12. Wgs84Aabb geometry: corners/center/size/validity/anti-meridian/tiles.
    rows = []
    for name, sw_lon, sw_lat, size_x, size_y in AABB_CASES:
        box = _make_aabb(sw_lon, sw_lat, size_x, size_y)
        split = box.split_over_anti_meridian()
        if split is None:
            split_out = None
        else:
            left, right = split
            split_out = {
                "left_sw": _pt(left.sw()),
                "left_size": [left.size().x, left.size().y],
                "right_sw": _pt(right.sw()),
                "right_size": [right.size().x, right.size().y],
            }
        rows.append(
            {
                "name": name,
                "sw_lon": sw_lon,
                "sw_lat": sw_lat,
                "size_x": size_x,
                "size_y": size_y,
                "valid": box.valid(),
                # The constructor may clamp size.y for valid boxes.
                "stored_size": [box.size().x, box.size().y],
                "sw": _pt(box.sw()),
                "se": _pt(box.se()),
                "ne": _pt(box.ne()),
                "nw": _pt(box.nw()),
                "center": _pt(box.center()),
                "vertices": [_pt(v) for v in box.vertices()],
                "contains_anti_meridian": box.contains_anti_meridian(),
                "split_over_anti_meridian": split_out,
                # num_tile_ids at levels 0..15 and the tile_level thresholds.
                "num_tile_ids": [box.num_tile_ids(lv) for lv in range(16)],
                "tile_level_min8": box.tile_level(8),
                "tile_level_min2": box.tile_level(2),
            }
        )
    data["wgs84_aabb"] = rows

    # 13. Wgs84Aabb.contains: each point against each AABB case.
    rows = []
    for box_name, sw_lon, sw_lat, size_x, size_y in AABB_CASES:
        box = _make_aabb(sw_lon, sw_lat, size_x, size_y)
        for point_name, plon, plat in AABB_CONTAINS_POINTS:
            rows.append(
                {
                    "box": box_name,
                    "point": point_name,
                    "point_lon": plon,
                    "point_lat": plat,
                    "contains": box.contains(Wgs84(plon, plat)),
                }
            )
    data["wgs84_aabb_contains"] = rows

    # 14. Wgs84Aabb.intersects: full ordered pairwise matrix (verifies symmetry).
    rows = []
    for a_name, a_sw_lon, a_sw_lat, a_sx, a_sy in AABB_CASES:
        for b_name, b_sw_lon, b_sw_lat, b_sx, b_sy in AABB_CASES:
            a = _make_aabb(a_sw_lon, a_sw_lat, a_sx, a_sy)
            b = _make_aabb(b_sw_lon, b_sw_lat, b_sx, b_sy)
            rows.append(
                {
                    "a": a_name,
                    "b": b_name,
                    "intersects": a.intersects(b),
                }
            )
    data["wgs84_aabb_intersects"] = rows

    # 15. Polygon orientation + validity (base Polygon, raw lon/lat plane).
    rows = []
    for name, ptype_int, verts in POLYGON_CASES:
        ptype = PolygonType(ptype_int)
        poly = Polygon(ptype, [Wgs84(lon, lat) for lon, lat in verts])
        rows.append(
            {
                "name": name,
                "polygon_type": ptype_int,
                "vertices": [list(v) for v in verts],
                "orientation": int(poly.orientation()),
                "is_valid": poly.is_valid(),
            }
        )
    data["polygon_orientation"] = rows

    # 16. Wgs84Polygon: aaBb, median (centroid), is_valid.
    rows = []
    for name, verts in WGS84_POLYGON_CASES:
        poly = Wgs84Polygon(vertices=[Wgs84(lon, lat) for lon, lat in verts])
        bb = poly.aa_bb()
        med = poly.median()
        rows.append(
            {
                "name": name,
                "vertices": [list(v) for v in verts],
                "is_valid": poly.is_valid(),
                "aabb_sw": _pt(bb.sw()),
                "aabb_size": [bb.size().x, bb.size().y],
                "median_lon": med.longitude(),
                "median_lat": med.latitude(),
            }
        )
    data["wgs84_polygon"] = rows

    # 17. Wgs84Polygon.collides_with (SAT), ordered pairs.
    rows = []
    for a_name, a_verts, b_name, b_verts in WGS84_POLYGON_COLLISION_PAIRS:
        a = Wgs84Polygon(vertices=[Wgs84(lon, lat) for lon, lat in a_verts])
        b = Wgs84Polygon(vertices=[Wgs84(lon, lat) for lon, lat in b_verts])
        rows.append(
            {
                "a": a_name,
                "a_vertices": [list(v) for v in a_verts],
                "b": b_name,
                "b_vertices": [list(v) for v in b_verts],
                "a_collides_b": a.collides_with(b),
                "b_collides_a": b.collides_with(a),
            }
        )
    data["wgs84_polygon_collision"] = rows

    out_path = os.path.join(REPO_ROOT, "test-vectors", "parity_vectors.json")
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print(f"Wrote {out_path}")
    print(f"Sections: {[k for k in data if not k.startswith('_')]}")


if __name__ == "__main__":
    main()
