// SPDX-License-Identifier: MIT
//! Axis-aligned bounding boxes in NDS coordinate space.
//!
//! Faithful port of `python/src/ndslive/math/bounding_box.py`.

use crate::tileid::PackedTileId;
use crate::wgs84::Wgs84;

/// Axis-aligned bounding box in NDS coordinates (32-bit integers).
///
/// - `min_x` / `max_x`: longitude (32-bit signed)
/// - `min_y` / `max_y`: latitude (31-bit signed)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct NdsBoundingBox {
    /// SW corner longitude (NDS coords).
    pub min_x: i32,
    /// SW corner latitude (NDS coords).
    pub min_y: i32,
    /// NE corner longitude (NDS coords).
    pub max_x: i32,
    /// NE corner latitude (NDS coords).
    pub max_y: i32,
}

impl NdsBoundingBox {
    /// Construct a bounding box from explicit corner coordinates.
    pub fn new(min_x: i32, min_y: i32, max_x: i32, max_y: i32) -> Self {
        NdsBoundingBox {
            min_x,
            min_y,
            max_x,
            max_y,
        }
    }

    /// Check whether this bounding box intersects (overlaps) `other`.
    ///
    /// Boundaries are inclusive: touching edges count as intersecting, matching
    /// the Python reference.
    pub fn intersects(&self, other: &NdsBoundingBox) -> bool {
        !(self.max_x < other.min_x
            || self.min_x > other.max_x
            || self.max_y < other.min_y
            || self.min_y > other.max_y)
    }

    /// Check whether this bounding box fully contains `other`.
    pub fn contains(&self, other: &NdsBoundingBox) -> bool {
        self.min_x <= other.min_x
            && self.max_x >= other.max_x
            && self.min_y <= other.min_y
            && self.max_y >= other.max_y
    }

    /// Create a bounding box covering a tile's area.
    ///
    /// Uses the tile's (exclusive) NE corner directly, matching the Python
    /// `from_tile`.
    ///
    /// Note: NDS coordinates are 32-bit; for very large tiles (e.g. a level-0
    /// tile whose exclusive NE corner is `2^31`) the corner does not fit in a
    /// signed `i32` and wraps. The Python reference uses unbounded integers, so
    /// this is the one place the fixed-width Rust port can differ at the extreme
    /// boundary. All other corners (level >= 1, or any tile not touching the
    /// antimeridian / pole) are representable exactly.
    pub fn from_tile(tile: &PackedTileId) -> Self {
        let (sw_x, sw_y) = tile.south_west_corner();
        let (ne_x, ne_y) = tile.north_east_corner();
        NdsBoundingBox {
            min_x: sw_x as i32,
            min_y: sw_y as i32,
            max_x: ne_x as i32,
            max_y: ne_y as i32,
        }
    }

    /// Create a bounding box from WGS84 corner coordinates.
    ///
    /// `sw` is the south-west (min lon/lat) corner, `ne` the north-east corner.
    pub fn from_wgs84_corners(sw: &Wgs84, ne: &Wgs84) -> Self {
        let (min_x, min_y) = sw.to_nds_coordinates();
        let (max_x, max_y) = ne.to_nds_coordinates();
        NdsBoundingBox {
            min_x,
            min_y,
            max_x,
            max_y,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn identical_boxes_intersect_and_contain() {
        let a = NdsBoundingBox::new(0, 0, 100, 100);
        let b = NdsBoundingBox::new(0, 0, 100, 100);
        assert!(a.intersects(&b));
        assert!(a.contains(&b));
    }

    #[test]
    fn disjoint_boxes() {
        let a = NdsBoundingBox::new(0, 0, 100, 100);
        let b = NdsBoundingBox::new(200, 200, 300, 300);
        assert!(!a.intersects(&b));
        assert!(!a.contains(&b));
    }

    #[test]
    fn partial_overlap_no_containment() {
        let a = NdsBoundingBox::new(0, 0, 100, 100);
        let b = NdsBoundingBox::new(50, 50, 150, 150);
        assert!(a.intersects(&b));
        assert!(!a.contains(&b));
    }

    #[test]
    fn inner_box_contained() {
        let a = NdsBoundingBox::new(0, 0, 100, 100);
        let b = NdsBoundingBox::new(10, 10, 20, 20);
        assert!(a.intersects(&b));
        assert!(a.contains(&b));
    }

    #[test]
    fn from_tile_matches_corners() {
        let t = PackedTileId::from_i64(131072).unwrap();
        let bb = NdsBoundingBox::from_tile(&t);
        assert_eq!(bb.min_x, 0);
        assert_eq!(bb.min_y, 0);
    }
}
