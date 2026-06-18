#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
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
    Wgs84,
    MortonCode,
    PackedTileId,
    NdsBoundingBox,
    get_tile_ids_for_bounding_box,
    bounding_box_from_tile_ids,
)

# ---------------------------------------------------------------------------
# Input fixtures
# ---------------------------------------------------------------------------

# (lon, lat) sample points: cities, origin, sign variants, near-boundaries.
WGS84_POINTS = [
    (0.0, 0.0),
    (13.404954, 52.520008),    # Berlin
    (11.585, 48.137),          # Munich
    (-122.4194, 37.7749),      # San Francisco
    (151.2093, -33.8688),      # Sydney
    (-43.1729, -22.9068),      # Rio de Janeiro
    (139.6917, 35.6895),       # Tokyo
    (-0.1276, 51.5072),        # London
    (179.9, 0.0),
    (-179.9, 0.0),
    (180.0, 90.0),             # exercises clamping/wrapping
    (-180.0, -90.0),
    (179.999999, 89.999999),
    (-0.000001, -0.000001),    # near-origin negatives (floor vs truncate)
    (360.5, 0.0),              # wrap > 360
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
    (0, 0), (1, 0),
    (0, 1), (3, 1), (7, 1),
    (0, 2), (4, 2), (31, 2),
    (0, 13), (12345, 13),
    (0, 14), (1 << 20, 14),
    (0, 15), ((1 << 31) - 1, 15), (1234567, 15),
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
        rows.append({
            "lon": lon, "lat": lat,
            "normalized_lon": w.x, "normalized_lat": w.y,
            "nds_x": x_nds, "nds_y": y_nds,
        })
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
        rows.append({
            "x": x, "y": y,
            "morton": str(m.value()),   # may exceed 2^53; transport as string
            "decoded_x": dx, "decoded_y": dy,
        })
    data["morton"] = rows

    # 4. PackedTileId from tile index: value/level/morton/size/corners/center
    rows = []
    for morton_number, level in TILE_INDEX:
        t = PackedTileId.from_tile_index(morton_number, level)
        rows.append({
            "morton_number": morton_number, "level": level,
            "value": t.value,
            "computed_level": t.level(),
            "computed_morton_number": t.morton_number(),
            "size": t.size(),
            "sw": list(t.south_west_corner()),
            "ne": list(t.north_east_corner()),
            "center": list(t.center()),
        })
    data["packed_tile_from_index"] = rows

    # 5. Neighbours (report neighbour .value)
    rows = []
    for morton_number, level in TILE_INDEX:
        if level == 0:
            continue  # level 0 neighbour behaviour is degenerate; skip
        t = PackedTileId.from_tile_index(morton_number, level)
        rows.append({
            "morton_number": morton_number, "level": level,
            "west": t.west_neighbour().value,
            "east": t.east_neighbour().value,
            "south": t.south_neighbour().value,
            "north": t.north_neighbour().value,
        })
    data["tile_neighbours"] = rows

    # 6. from_morton_and_level (containing tile)
    rows = []
    for x, y, level in FROM_MORTON_LEVEL:
        m = MortonCode.from_nds_coordinates(x, y)
        t = PackedTileId.from_morton_and_level(m, level)
        rows.append({
            "x": x, "y": y, "level": level,
            "value": t.value,
            "computed_level": t.level(),
            "computed_morton_number": t.morton_number(),
        })
    data["from_morton_and_level"] = rows

    # 7. get_tile_ids_for_bounding_box
    rows = []
    for sw_x, sw_y, ne_x, ne_y, level in TILES_FOR_BBOX:
        tiles = get_tile_ids_for_bounding_box(sw_x, sw_y, ne_x, ne_y, level)
        rows.append({
            "sw_x": sw_x, "sw_y": sw_y, "ne_x": ne_x, "ne_y": ne_y,
            "level": level,
            "tile_values": [t.value for t in tiles],
        })
    data["tiles_for_bbox"] = rows

    # 8. bounding_box_from_tile_ids
    rows = []
    for morton_number, level in TILE_INDEX:
        if level == 0:
            continue
        t = PackedTileId.from_tile_index(morton_number, level)
        bbox = bounding_box_from_tile_ids([t])
        rows.append({
            "tile_values": [t.value],
            "result": list(bbox),
        })
    data["bbox_from_tiles"] = rows

    # 9. NdsBoundingBox operations
    rows = []
    boxes = [
        (0, 0, 100, 100),
        (50, 50, 150, 150),
        (200, 200, 300, 300),
        (10, 10, 20, 20),
    ]
    for i, (ax, ay, axx, ayy) in enumerate(boxes):
        for j, (bx, by, bxx, byy) in enumerate(boxes):
            a = NdsBoundingBox(ax, ay, axx, ayy)
            b = NdsBoundingBox(bx, by, bxx, byy)
            rows.append({
                "a": [ax, ay, axx, ayy], "b": [bx, by, bxx, byy],
                "intersects": a.intersects(b),
                "a_contains_b": a.contains(b),
            })
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
        rows.append({
            "sw": [sw_lon, sw_lat], "ne": [ne_lon, ne_lat],
            "min_x": bbox.min_x, "min_y": bbox.min_y,
            "max_x": bbox.max_x, "max_y": bbox.max_y,
        })
    data["nds_bbox_from_wgs84"] = rows

    # 11. Floating-point helpers (compare with FLOAT_TOLERANCE)
    rows = []
    pairs = [
        ((13.404954, 52.520008), (11.585, 48.137)),   # Berlin -> Munich
        ((0.0, 0.0), (0.0, 1.0)),
        ((-122.4194, 37.7749), (139.6917, 35.6895)),  # SF -> Tokyo
    ]
    for (lon1, lat1), (lon2, lat2) in pairs:
        a = Wgs84(lon=lon1, lat=lat1)
        b = Wgs84(lon=lon2, lat=lat2)
        rows.append({
            "a": [lon1, lat1], "b": [lon2, lat2],
            "distance_m": a.distance_to(b),
            "bearing_rad": a.bearing_from(b),
        })
    data["distance_bearing"] = rows

    rows = []
    for nds_x, nds_y, at_lat in [(1 << 20, 1 << 20, 0.0),
                                 (1 << 18, 1 << 18, 48.137),
                                 (1 << 22, 1 << 22, 60.0)]:
        w_m, h_m = Wgs84.nds_distance_to_meters(nds_x, nds_y, at_lat)
        rows.append({
            "nds_x": nds_x, "nds_y": nds_y, "at_latitude": at_lat,
            "width_m": w_m, "height_m": h_m,
        })
    data["nds_distance_to_meters"] = rows

    out_path = os.path.join(REPO_ROOT, "test-vectors", "parity_vectors.json")
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print(f"Wrote {out_path}")
    print(f"Sections: {[k for k in data if not k.startswith('_')]}")


if __name__ == "__main__":
    main()
