// SPDX-License-Identifier: BSD-3-Clause
//! Golden parity tests: load `test-vectors/parity_vectors.json` (the
//! language-neutral contract generated from the Python reference) and assert
//! that this Rust port agrees bit-for-bit on integers and within tolerance on
//! floats.

use std::path::PathBuf;

use ndslive_math::{
    bounding_box_from_tile_ids, get_tile_ids_for_bounding_box, MortonCode, NdsBoundingBox,
    PackedTileId, Wgs84,
};
use serde::Deserialize;

const FLOAT_TOLERANCE: f64 = 1e-6;

#[derive(Debug, Deserialize)]
struct Vectors {
    #[serde(rename = "_meta")]
    meta: Meta,
    wgs84_to_nds: Vec<Wgs84ToNds>,
    nds_to_wgs84: Vec<NdsToWgs84>,
    morton: Vec<MortonVec>,
    packed_tile_from_index: Vec<PackedTileFromIndex>,
    tile_neighbours: Vec<TileNeighbours>,
    from_morton_and_level: Vec<FromMortonAndLevel>,
    tiles_for_bbox: Vec<TilesForBbox>,
    bbox_from_tiles: Vec<BboxFromTiles>,
    nds_bbox_ops: Vec<NdsBboxOps>,
    nds_bbox_from_wgs84: Vec<NdsBboxFromWgs84>,
    distance_bearing: Vec<DistanceBearing>,
    nds_distance_to_meters: Vec<NdsDistanceToMeters>,
}

#[derive(Debug, Deserialize)]
struct Meta {
    float_tolerance: f64,
}

#[derive(Debug, Deserialize)]
struct Wgs84ToNds {
    lon: f64,
    lat: f64,
    normalized_lon: f64,
    normalized_lat: f64,
    nds_x: i32,
    nds_y: i32,
}

#[derive(Debug, Deserialize)]
struct NdsToWgs84 {
    x: i32,
    y: i32,
    lon: f64,
    lat: f64,
}

#[derive(Debug, Deserialize)]
struct MortonVec {
    x: i32,
    y: i32,
    morton: String,
    decoded_x: i32,
    decoded_y: i32,
}

#[derive(Debug, Deserialize)]
struct PackedTileFromIndex {
    morton_number: u32,
    level: u32,
    value: i32,
    computed_level: u32,
    computed_morton_number: u32,
    size: i64,
    sw: [i64; 2],
    ne: [i64; 2],
    center: [i64; 2],
}

#[derive(Debug, Deserialize)]
struct TileNeighbours {
    morton_number: u32,
    level: u32,
    west: i32,
    east: i32,
    south: i32,
    north: i32,
}

#[derive(Debug, Deserialize)]
struct FromMortonAndLevel {
    x: i32,
    y: i32,
    level: u32,
    value: i32,
    computed_level: u32,
    computed_morton_number: u32,
}

#[derive(Debug, Deserialize)]
struct TilesForBbox {
    sw_x: i64,
    sw_y: i64,
    ne_x: i64,
    ne_y: i64,
    level: u32,
    tile_values: Vec<i32>,
}

#[derive(Debug, Deserialize)]
struct BboxFromTiles {
    tile_values: Vec<i32>,
    result: [i64; 4],
}

#[derive(Debug, Deserialize)]
struct NdsBboxOps {
    a: [i32; 4],
    b: [i32; 4],
    intersects: bool,
    a_contains_b: bool,
}

#[derive(Debug, Deserialize)]
struct NdsBboxFromWgs84 {
    sw: [f64; 2],
    ne: [f64; 2],
    min_x: i32,
    min_y: i32,
    max_x: i32,
    max_y: i32,
}

#[derive(Debug, Deserialize)]
struct DistanceBearing {
    a: [f64; 2],
    b: [f64; 2],
    distance_m: f64,
    bearing_rad: f64,
}

#[derive(Debug, Deserialize)]
struct NdsDistanceToMeters {
    nds_x: i32,
    nds_y: i32,
    at_latitude: f64,
    width_m: f64,
    height_m: f64,
}

fn load() -> Vectors {
    let mut path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    path.pop(); // up from rust/ to repo root
    path.push("test-vectors");
    path.push("parity_vectors.json");
    let text = std::fs::read_to_string(&path)
        .unwrap_or_else(|e| panic!("failed to read {}: {e}", path.display()));
    serde_json::from_str(&text).expect("failed to parse parity_vectors.json")
}

fn approx(a: f64, b: f64, tol: f64) -> bool {
    if a == b {
        return true;
    }
    // Absolute-or-relative tolerance (handles both tiny and large magnitudes).
    let diff = (a - b).abs();
    diff <= tol || diff <= tol * a.abs().max(b.abs())
}

#[test]
fn meta_tolerance_is_expected() {
    let v = load();
    assert!(approx(v.meta.float_tolerance, FLOAT_TOLERANCE, 0.0));
}

#[test]
fn wgs84_to_nds() {
    let v = load();
    assert!(!v.wgs84_to_nds.is_empty());
    for row in &v.wgs84_to_nds {
        let p = Wgs84::new(row.lon, row.lat);
        assert!(
            approx(p.lon, row.normalized_lon, FLOAT_TOLERANCE),
            "normalized lon for ({}, {}): got {}, want {}",
            row.lon,
            row.lat,
            p.lon,
            row.normalized_lon
        );
        assert!(
            approx(p.lat, row.normalized_lat, FLOAT_TOLERANCE),
            "normalized lat for ({}, {}): got {}, want {}",
            row.lon,
            row.lat,
            p.lat,
            row.normalized_lat
        );
        let (x, y) = p.to_nds_coordinates();
        assert_eq!(x, row.nds_x, "nds_x for ({}, {})", row.lon, row.lat);
        assert_eq!(y, row.nds_y, "nds_y for ({}, {})", row.lon, row.lat);
    }
}

#[test]
fn nds_to_wgs84() {
    let v = load();
    assert!(!v.nds_to_wgs84.is_empty());
    for row in &v.nds_to_wgs84 {
        let p = Wgs84::from_nds_coordinates(row.x, row.y);
        assert!(
            approx(p.lon, row.lon, FLOAT_TOLERANCE),
            "lon for ({}, {}): got {}, want {}",
            row.x,
            row.y,
            p.lon,
            row.lon
        );
        assert!(
            approx(p.lat, row.lat, FLOAT_TOLERANCE),
            "lat for ({}, {}): got {}, want {}",
            row.x,
            row.y,
            p.lat,
            row.lat
        );
    }
}

#[test]
fn morton() {
    let v = load();
    assert!(!v.morton.is_empty());
    for row in &v.morton {
        let expected: u64 = row.morton.parse().expect("morton decimal string");
        let m = MortonCode::from_nds_coordinates(row.x, row.y);
        assert_eq!(m.value(), expected, "encode ({}, {})", row.x, row.y);
        let (dx, dy) = m.to_nds_coordinates();
        assert_eq!(dx, row.decoded_x, "decoded_x ({}, {})", row.x, row.y);
        assert_eq!(dy, row.decoded_y, "decoded_y ({}, {})", row.x, row.y);
    }
}

#[test]
fn packed_tile_from_index() {
    let v = load();
    assert!(!v.packed_tile_from_index.is_empty());
    for row in &v.packed_tile_from_index {
        let t = PackedTileId::from_tile_index(row.morton_number, row.level).unwrap();
        assert_eq!(
            t.value(),
            row.value,
            "value m={} l={}",
            row.morton_number,
            row.level
        );
        assert_eq!(
            t.level(),
            row.computed_level,
            "level m={} l={}",
            row.morton_number,
            row.level
        );
        assert_eq!(
            t.morton_number(),
            row.computed_morton_number,
            "morton_number m={} l={}",
            row.morton_number,
            row.level
        );
        assert_eq!(
            t.size(),
            row.size,
            "size m={} l={}",
            row.morton_number,
            row.level
        );
        assert_eq!(
            t.south_west_corner(),
            (row.sw[0], row.sw[1]),
            "sw m={} l={}",
            row.morton_number,
            row.level
        );
        assert_eq!(
            t.north_east_corner(),
            (row.ne[0], row.ne[1]),
            "ne m={} l={}",
            row.morton_number,
            row.level
        );
        assert_eq!(
            t.center(),
            (row.center[0], row.center[1]),
            "center m={} l={}",
            row.morton_number,
            row.level
        );
    }
}

#[test]
fn tile_neighbours() {
    let v = load();
    assert!(!v.tile_neighbours.is_empty());
    for row in &v.tile_neighbours {
        let t = PackedTileId::from_tile_index(row.morton_number, row.level).unwrap();
        assert_eq!(
            t.west_neighbour().value(),
            row.west,
            "west m={} l={}",
            row.morton_number,
            row.level
        );
        assert_eq!(
            t.east_neighbour().value(),
            row.east,
            "east m={} l={}",
            row.morton_number,
            row.level
        );
        assert_eq!(
            t.south_neighbour().value(),
            row.south,
            "south m={} l={}",
            row.morton_number,
            row.level
        );
        assert_eq!(
            t.north_neighbour().value(),
            row.north,
            "north m={} l={}",
            row.morton_number,
            row.level
        );
    }
}

#[test]
fn from_morton_and_level() {
    let v = load();
    assert!(!v.from_morton_and_level.is_empty());
    for row in &v.from_morton_and_level {
        let m = MortonCode::from_nds_coordinates(row.x, row.y);
        let t = PackedTileId::from_morton_and_level(m, row.level).unwrap();
        assert_eq!(
            t.value(),
            row.value,
            "value x={} y={} l={}",
            row.x,
            row.y,
            row.level
        );
        assert_eq!(
            t.level(),
            row.computed_level,
            "level x={} y={} l={}",
            row.x,
            row.y,
            row.level
        );
        assert_eq!(
            t.morton_number(),
            row.computed_morton_number,
            "morton_number x={} y={} l={}",
            row.x,
            row.y,
            row.level
        );
    }
}

#[test]
fn tiles_for_bbox() {
    let v = load();
    assert!(!v.tiles_for_bbox.is_empty());
    for row in &v.tiles_for_bbox {
        let tiles =
            get_tile_ids_for_bounding_box(row.sw_x, row.sw_y, row.ne_x, row.ne_y, row.level);
        let values: Vec<i32> = tiles.iter().map(|t| t.value()).collect();
        assert_eq!(
            values, row.tile_values,
            "tiles_for_bbox {:?}",
            row.tile_values
        );
    }
}

#[test]
fn bbox_from_tiles() {
    let v = load();
    assert!(!v.bbox_from_tiles.is_empty());
    for row in &v.bbox_from_tiles {
        let tiles: Vec<PackedTileId> = row
            .tile_values
            .iter()
            .map(|&val| PackedTileId::from_i64(val as i64).unwrap())
            .collect();
        let bbox = bounding_box_from_tile_ids(&tiles).unwrap();
        assert_eq!(
            [bbox.0, bbox.1, bbox.2, bbox.3],
            row.result,
            "bbox_from_tiles {:?}",
            row.tile_values
        );
    }
}

#[test]
fn nds_bbox_ops() {
    let v = load();
    assert!(!v.nds_bbox_ops.is_empty());
    for row in &v.nds_bbox_ops {
        let a = NdsBoundingBox::new(row.a[0], row.a[1], row.a[2], row.a[3]);
        let b = NdsBoundingBox::new(row.b[0], row.b[1], row.b[2], row.b[3]);
        assert_eq!(
            a.intersects(&b),
            row.intersects,
            "intersects a={:?} b={:?}",
            row.a,
            row.b
        );
        assert_eq!(
            a.contains(&b),
            row.a_contains_b,
            "contains a={:?} b={:?}",
            row.a,
            row.b
        );
    }
}

#[test]
fn nds_bbox_from_wgs84() {
    let v = load();
    assert!(!v.nds_bbox_from_wgs84.is_empty());
    for row in &v.nds_bbox_from_wgs84 {
        let sw = Wgs84::new(row.sw[0], row.sw[1]);
        let ne = Wgs84::new(row.ne[0], row.ne[1]);
        let bb = NdsBoundingBox::from_wgs84_corners(&sw, &ne);
        assert_eq!(bb.min_x, row.min_x, "min_x sw={:?} ne={:?}", row.sw, row.ne);
        assert_eq!(bb.min_y, row.min_y, "min_y sw={:?} ne={:?}", row.sw, row.ne);
        assert_eq!(bb.max_x, row.max_x, "max_x sw={:?} ne={:?}", row.sw, row.ne);
        assert_eq!(bb.max_y, row.max_y, "max_y sw={:?} ne={:?}", row.sw, row.ne);
    }
}

#[test]
fn distance_bearing() {
    let v = load();
    assert!(!v.distance_bearing.is_empty());
    for row in &v.distance_bearing {
        let a = Wgs84::new(row.a[0], row.a[1]);
        let b = Wgs84::new(row.b[0], row.b[1]);
        // Mirror generate_vectors.py: a.distance_to(b), a.bearing_from(b).
        let dist = a.distance_to(&b);
        let bearing = a.bearing_from(&b);
        assert!(
            approx(dist, row.distance_m, FLOAT_TOLERANCE),
            "distance a={:?} b={:?}: got {}, want {}",
            row.a,
            row.b,
            dist,
            row.distance_m
        );
        assert!(
            approx(bearing, row.bearing_rad, FLOAT_TOLERANCE),
            "bearing a={:?} b={:?}: got {}, want {}",
            row.a,
            row.b,
            bearing,
            row.bearing_rad
        );
    }
}

#[test]
fn nds_distance_to_meters() {
    let v = load();
    assert!(!v.nds_distance_to_meters.is_empty());
    for row in &v.nds_distance_to_meters {
        let (w, h) = Wgs84::nds_distance_to_meters(row.nds_x, row.nds_y, row.at_latitude);
        assert!(
            approx(w, row.width_m, FLOAT_TOLERANCE),
            "width nds=({},{}) lat={}: got {}, want {}",
            row.nds_x,
            row.nds_y,
            row.at_latitude,
            w,
            row.width_m
        );
        assert!(
            approx(h, row.height_m, FLOAT_TOLERANCE),
            "height nds=({},{}) lat={}: got {}, want {}",
            row.nds_x,
            row.nds_y,
            row.at_latitude,
            h,
            row.height_m
        );
    }
}
