// SPDX-License-Identifier: BSD-3-Clause
//! `ndslive-math` — coordinate math, packed tile IDs, and Morton (Z-order)
//! codes for NDS.Live geographic tiling.
//!
//! This crate is a faithful Rust port of the Python reference implementation
//! (`ndslive.math`). It provides:
//!
//! - [`Wgs84`] — a WGS84 lon/lat/alt point with NDS coordinate conversion,
//!   distance and bearing helpers.
//! - [`MortonCode`] — a standalone Z-order encoder/decoder.
//! - [`PackedTileId`] — an NDS.Live Packed Tile ID with geometry accessors and
//!   neighbour traversal.
//! - [`NdsBoundingBox`] — a rectangle in NDS coordinate space.
//! - [`get_tile_ids_for_bounding_box`] / [`bounding_box_from_tile_ids`] — bulk
//!   tile enumeration helpers.
//!
//! # Example
//!
//! ```
//! use ndslive_math::{Wgs84, MortonCode, PackedTileId};
//!
//! // WGS84 -> NDS coordinates (uses floor, per the NDS recommendation).
//! let point = Wgs84::new(11.585, 48.137); // Munich
//! let (nds_x, nds_y) = point.to_nds_coordinates();
//!
//! // Find the level-13 tile containing the point.
//! let morton = MortonCode::from_nds_coordinates(nds_x, nds_y);
//! let tile = PackedTileId::from_morton_and_level(morton, 13).unwrap();
//!
//! let sw = tile.south_west_corner();
//! let east = tile.east_neighbour();
//! ```

pub mod bounding_box;
pub mod morton;
pub mod tileid;
pub mod wgs84;

pub use bounding_box::NdsBoundingBox;
pub use morton::MortonCode;
pub use tileid::{
    bounding_box_from_tile_ids, get_tile_ids_for_bounding_box, PackedTileId, TileIdError,
};
pub use wgs84::{Wgs84, EARTH_RADIUS_IN_METERS, LAT_NDS_DELTA, LON_NDS_DELTA, METERS_PER_DEGREE};
