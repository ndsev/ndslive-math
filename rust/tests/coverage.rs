// SPDX-License-Identifier: BSD-3-Clause
//
// Targeted tests for public-API paths not exercised by the parity vectors:
// error/Display formatting, alternate constructors, dimensions, bbox-from-tiles,
// normalization wrap branches, equality, and out-of-range Morton wrapping.

use ndslive_math::{bounding_box_from_tile_ids, MortonCode, PackedTileId, TileIdError, Wgs84};

#[test]
fn tile_id_error_display() {
    let e1: TileIdError = PackedTileId::from_tile_index(0, 16).unwrap_err();
    assert!(format!("{e1}").contains("Invalid level"));

    let e2 = PackedTileId::from_tile_index(99, 0).unwrap_err(); // max morton at level 0 is 1
    assert!(format!("{e2}").contains("morton"));

    let e3 = PackedTileId::new(0).unwrap_err(); // below the minimum packed tile id
    assert!(format!("{e3}").contains("must be >="));
}

#[test]
fn constructors() {
    // new() with a valid signed value (level 13, positive) and a level-15
    // negative value.
    let positive = PackedTileId::from_tile_index(12345, 13).unwrap().value();
    assert!(PackedTileId::new(positive).is_ok());
    let level15 = PackedTileId::from_tile_index(0, 15).unwrap().value();
    assert!(level15 < 0);
    assert!(PackedTileId::new(level15).is_ok());

    // from_i64 with an unsigned representation >= 2^32 (masked to low 32 bits).
    let t = PackedTileId::from_i64((1i64 << 32) + (1i64 << 16)).unwrap();
    assert_eq!(t.level(), 0);

    // from_morton_and_level rejects an invalid level.
    let m = MortonCode::from_nds_coordinates(0, 0);
    assert!(PackedTileId::from_morton_and_level(m, 16).is_err());
}

#[test]
fn added_tile_factories_and_grid_coordinates() {
    let tile = PackedTileId::from_tile_xy(3, 1, 1).unwrap();
    assert_eq!(tile.value(), 131079);
    assert_eq!(tile.x(), 3);
    assert_eq!(tile.y(), 1);
    assert_eq!(
        PackedTileId::from_value(tile.value()).unwrap().value(),
        tile.value()
    );
    assert_eq!(tile.center_wgs84(), (-45.0, -45.0));
    assert_eq!(tile.south_west_wgs84(), (-90.0, -90.0));
    assert_eq!(tile.north_east_wgs84(), (0.0, 0.0));
    assert_eq!(tile.wgs84_size(), (90.0, 90.0));
    assert_eq!(
        PackedTileId::wgs84_from_nds_coordinates(1i64 << 31, 1i64 << 30),
        (180.0, 90.0)
    );

    let from_nds = PackedTileId::from_nds_coordinates(-65537, -65537, 15).unwrap();
    let from_wgs =
        PackedTileId::from_wgs84(-0.005493205972015858, -0.005493205972015858, 15).unwrap();
    assert_eq!(from_nds.value(), -4);
    assert_eq!(from_wgs.value(), -4);
}

#[test]
fn added_tile_factory_validation() {
    assert!(PackedTileId::from_value(0).is_err());
    assert!(PackedTileId::from_tile_xy(0, 0, 16).is_err());

    let x_error = PackedTileId::from_tile_xy(4, 0, 1).unwrap_err();
    assert!(matches!(
        x_error,
        TileIdError::InvalidMortonNumber { morton: 4, .. }
    ));

    let y_error = PackedTileId::from_tile_xy(0, 2, 1).unwrap_err();
    assert!(matches!(
        y_error,
        TileIdError::InvalidMortonNumber { morton: 2, .. }
    ));

    assert!(PackedTileId::from_nds_coordinates(0, 0, 16).is_err());
    assert!(PackedTileId::from_wgs84(0.0, 0.0, 16).is_err());
}

#[test]
fn relative_neighbour_wrapping() {
    let tile = PackedTileId::from_tile_xy(0, 0, 1).unwrap();
    assert_eq!(tile.neighbour(1, 0), tile.east_neighbour());
    assert_eq!(tile.neighbour(0, 1), tile.north_neighbour());
    assert_eq!(
        tile.neighbour(-1, -1),
        PackedTileId::from_tile_xy(3, 1, 1).unwrap()
    );
    assert_eq!(tile.neighbour(4, 2), tile);
    assert_eq!(tile.neighbor(4, 2), tile.neighbour(4, 2));
}

#[test]
fn dimensions_and_displays() {
    let tile = PackedTileId::from_tile_index(12345, 13).unwrap();
    let (w, h) = tile.dimensions_in_meters();
    assert!(w > 0.0 && h > 0.0);

    assert!(format!("{tile}").contains("PackedTileId(value="));
    assert!(format!("{}", MortonCode::from_nds_coordinates(1, 1)).contains("MortonCode(value="));
}

#[test]
fn bbox_from_multiple_tiles() {
    // Empty -> None.
    assert!(bounding_box_from_tile_ids(&[]).is_none());

    // Several tiles -> the min/max-update loop runs over all four directions.
    let tiles = ndslive_math::get_tile_ids_for_bounding_box(0, 0, 1 << 28, 1 << 28, 3);
    assert!(tiles.len() >= 3);
    let mid = tiles[tiles.len() / 2];
    let ordered = [mid, tiles[0], tiles[tiles.len() - 1]];
    let (min_x, min_y, max_x, max_y) = bounding_box_from_tile_ids(&ordered).unwrap();
    assert!(min_x <= max_x && min_y <= max_y);
}

#[test]
fn wgs84_normalization_wrap_and_eq() {
    // Longitudes that need wrapping into [-180, 180) exercise both wrap branches.
    assert!((Wgs84::new(270.0, 0.0).lon - (-90.0)).abs() < 1e-9);
    assert!((Wgs84::new(-270.0, 0.0).lon - 90.0).abs() < 1e-9);

    // PartialEq (and the is_close_rel helper) + Display.
    let a = Wgs84::new(13.404954, 52.520008);
    let b = Wgs84::new(13.404954, 52.520008);
    assert_eq!(a, b);
    assert_ne!(a, Wgs84::new(11.585, 48.137));
    assert!(format!("{a}").contains("Wgs84(lon="));
}

#[test]
fn morton_out_of_range_y_wraps() {
    // y outside [-2^30, 2^30) exercises the wrap loops (x is full i32, so its
    // wrap loops are unreachable from this API).
    let (_, y) = MortonCode::from_nds_coordinates(0, 1 << 30).to_nds_coordinates();
    assert_eq!(y, -(1 << 30));
    let _ = MortonCode::from_nds_coordinates(0, -(1 << 30) - 1).to_nds_coordinates();
}
