// SPDX-License-Identifier: BSD-3-Clause
//! WGS84 axis-aligned bounding box.
//!
//! Port of the C++ `Wgs84AABB<T>` (`cpp/include/ndsmath/wgs84aabb.h`),
//! specialized to `f64`, and the Python reference
//! `python/src/ndslive/math/wgs84_aabb.py`. The box is stored as a south-west
//! corner ([`Wgs84`]) plus a raw [`Vec2`] size (a `(dx, dy)` extent that is
//! *not* normalized).
//!
//! The geometry layer deliberately uses the power-of-two NDS deltas
//! ([`crate::wgs84::LON_NDS_DELTA_POW2`] etc.) so antimeridian handling and
//! tile-from-index construction match the C++ reference bit-for-bit.

use crate::morton::MortonCode;
use crate::tileid::PackedTileId;
use crate::vec2::Vec2;
use crate::wgs84::{Wgs84, LON_MAX, LON_MIN, LON_NDS_DELTA_POW2};

/// A WGS84 axis-aligned bounding box defined by a SW corner and a size.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Wgs84Aabb {
    sw: Wgs84,
    size: Vec2,
}

impl Default for Wgs84Aabb {
    /// The default box: `sw = (0, 0)`, `size = (0, 0)`. `valid()` is **true**.
    fn default() -> Self {
        Wgs84Aabb::new(Wgs84::new(0.0, 0.0), Vec2::new(0.0, 0.0))
    }
}

impl Wgs84Aabb {
    /// Construct an AABB from a south-west corner and a size.
    ///
    /// After storing, if the box is [`Wgs84Aabb::valid`], the height is clamped
    /// so the top never exceeds +90 degrees (`excessHeight` correction). An
    /// invalid box stores `size` unmodified.
    pub fn new(sw: Wgs84, size: Vec2) -> Self {
        let mut aabb = Wgs84Aabb { sw, size };
        if !aabb.valid() {
            return aabb;
        }
        let excess_height = 90.0 - aabb.sw.lat - aabb.size.y;
        if excess_height < 0.0 {
            aabb.size.y += excess_height;
        }
        aabb
    }

    /// Construct an AABB covering a tile (Path A: via [`Wgs84::from_morton_code`]).
    ///
    /// Mirrors the C++ `Wgs84AABB(PackedTileId)` constructor: the SW/NE NDS
    /// corners are wrapped into a [`MortonCode`] and converted via
    /// [`Wgs84::from_morton_code`], so both axes are scaled by `360 / 2^32`.
    pub fn from_tile(tile_id: &PackedTileId) -> Self {
        let (sw_x, sw_y) = tile_id.south_west_corner();
        let (ne_x, ne_y) = tile_id.north_east_corner();

        let sw_corner =
            Wgs84::from_morton_code(MortonCode::from_nds_coordinates(sw_x as i32, sw_y as i32));
        let ne_corner =
            Wgs84::from_morton_code(MortonCode::from_nds_coordinates(ne_x as i32, ne_y as i32));

        let size = Vec2::new(sw_corner.lon - ne_corner.lon, sw_corner.lat - ne_corner.lat).abs();
        Wgs84Aabb::new(sw_corner, size)
    }

    /// Construct an AABB from a center, a soft tile-count limit, and a level.
    pub fn from_center_and_tile_limit(center: Wgs84, soft_limit: u32, level: u16) -> Self {
        let target_aspect_ratio = 0.7; // approx. height / width
        let tile_width = 180.0 / ((1u64 << level) as f64);
        let target_size = (soft_limit as f64).sqrt() * tile_width;
        let target_size_vec = Vec2::new(
            target_size / target_aspect_ratio,
            target_size * target_aspect_ratio,
        );
        let half = target_size_vec * 0.5;
        let new_sw = Wgs84::new(center.lon - half.x, center.lat - half.y);
        Wgs84Aabb::new(new_sw, target_size_vec)
    }

    /// Whether the box size is within reasonable bounds.
    ///
    /// `0 <= size.x <= 360` and `0 <= size.y <= 180`.
    pub fn valid(&self) -> bool {
        self.size.x >= 0.0 && self.size.y >= 0.0 && self.size.x <= 360.0 && self.size.y <= 180.0
    }

    /// The south-west corner.
    pub fn sw(&self) -> Wgs84 {
        self.sw
    }

    /// The north-east corner (`sw + size`, re-normalized).
    pub fn ne(&self) -> Wgs84 {
        Wgs84::new(self.sw.lon + self.size.x, self.sw.lat + self.size.y)
    }

    /// The north-west corner.
    pub fn nw(&self) -> Wgs84 {
        Wgs84::new(self.sw.lon, self.sw.lat + self.size.y)
    }

    /// The south-east corner.
    pub fn se(&self) -> Wgs84 {
        Wgs84::new(self.sw.lon + self.size.x, self.sw.lat)
    }

    /// All four corners, CCW from SW: `[sw, se, ne, nw]`.
    pub fn vertices(&self) -> [Wgs84; 4] {
        [self.sw(), self.se(), self.ne(), self.nw()]
    }

    /// The raw `(dx, dy)` size of the box.
    pub fn size(&self) -> Vec2 {
        self.size
    }

    /// Whether the horizontal extent crosses the anti-meridian (+/-180).
    pub fn contains_anti_meridian(&self) -> bool {
        self.sw.lon + self.size.x > LON_MAX + LON_NDS_DELTA_POW2
    }

    /// The center coordinate (`sw + size * 0.5`, re-normalized).
    pub fn center(&self) -> Wgs84 {
        let half = self.size * 0.5;
        Wgs84::new(self.sw.lon + half.x, self.sw.lat + half.y)
    }

    /// Split a box crossing the anti-meridian into a left and right half.
    ///
    /// Only meaningful when [`Wgs84Aabb::contains_anti_meridian`] is true.
    /// Returns `None` if the box does not actually extend past `LON_MAX`.
    pub fn split_over_anti_meridian(&self) -> Option<(Wgs84Aabb, Wgs84Aabb)> {
        let width_after_am = self.sw.lon + self.size.x - LON_MAX;
        if width_after_am > 0.0 {
            let width_before_am = self.size.x - width_after_am;
            let left = Wgs84Aabb::new(self.sw, Vec2::new(width_before_am, self.size.y));
            let right = Wgs84Aabb::new(
                Wgs84::new(LON_MIN, self.sw.lat),
                Vec2::new(width_after_am, self.size.y),
            );
            return Some((left, right));
        }
        None
    }

    /// The Mercator-projection vertical stretch factor.
    ///
    /// Transcendental; not part of the cross-language parity vectors (asserted
    /// only for finiteness in unit tests).
    pub fn avg_mercator_stretch(&self) -> f64 {
        let lat_top = (self.sw.lat + self.size.y).to_radians();
        let lat_bottom = self.sw.lat.to_radians();

        fn rad_to_mercator_lat(wgs84_lat: f64) -> f64 {
            (wgs84_lat - std::f64::consts::FRAC_PI_2).sin().atanh()
        }

        (rad_to_mercator_lat(lat_top) - rad_to_mercator_lat(lat_bottom)) / self.size.y.to_radians()
    }

    /// Approximate number of tiles at level `lv` contained in this box.
    ///
    /// Mirrors the C++ `numTileIds`: `tileWidth = 180 / float(2^lv)` and a
    /// component-wise `ceil` of `size / tileWidth`. Returns a signed count
    /// because an invalid (negative-size) box can yield negative values, which
    /// the parity vectors lock in.
    pub fn num_tile_ids(&self, lv: u32) -> i64 {
        let tile_width = 180.0 / ((1u64 << lv) as f64);
        let tiles_per_dim_x = (self.size.x / tile_width).ceil();
        let tiles_per_dim_y = (self.size.y / tile_width).ceil();
        (tiles_per_dim_x * tiles_per_dim_y) as i64
    }

    /// First level (0..15) whose tile count is at least `min_num_tiles`.
    ///
    /// Returns 15 if no level in `0..15` reaches the threshold.
    pub fn tile_level(&self, min_num_tiles: i64) -> u8 {
        for result_tile_level in 0..16u32 {
            if self.num_tile_ids(result_tile_level) >= min_num_tiles {
                return result_tile_level as u8;
            }
        }
        15
    }

    /// Whether `point` lies within the box (inclusive on all edges).
    pub fn contains(&self, point: &Wgs84) -> bool {
        point.lon >= self.sw.lon
            && point.lon <= self.sw.lon + self.size.x
            && point.lat >= self.sw.lat
            && point.lat <= self.sw.lat + self.size.y
    }

    /// Axis-aligned interval-overlap test against another box.
    ///
    /// This is the *fixed* test: a pure interval overlap on longitude and
    /// latitude. Edge-touching counts as intersecting; it correctly detects
    /// cross-shaped overlaps and never recurses on disjoint boxes.
    pub fn intersects(&self, other: &Wgs84Aabb) -> bool {
        let a_max_x = self.sw.lon + self.size.x;
        let a_max_y = self.sw.lat + self.size.y;
        let b_max_x = other.sw.lon + other.size.x;
        let b_max_y = other.sw.lat + other.size.y;
        self.sw.lon <= b_max_x
            && a_max_x >= other.sw.lon
            && self.sw.lat <= b_max_y
            && a_max_y >= other.sw.lat
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::wgs84::LAT_MAX;

    #[test]
    fn construction_and_corners() {
        let b = Wgs84Aabb::new(Wgs84::new(0.0, 10.0), Vec2::new(20.0, 10.0));
        assert!(b.valid());
        assert_eq!(b.sw(), Wgs84::new(0.0, 10.0));
        assert_eq!(b.ne(), Wgs84::new(20.0, 20.0));
        assert_eq!(b.nw(), Wgs84::new(0.0, 20.0));
        assert_eq!(b.se(), Wgs84::new(20.0, 10.0));
        assert_eq!(b.center(), Wgs84::new(10.0, 15.0));
        assert_eq!(b.size(), Vec2::new(20.0, 10.0));
        let v = b.vertices();
        assert_eq!(v[0], Wgs84::new(0.0, 10.0));
        assert_eq!(v[2], Wgs84::new(20.0, 20.0));
    }

    #[test]
    fn excess_height_clamp() {
        let b = Wgs84Aabb::new(Wgs84::new(0.0, 85.0), Vec2::new(10.0, 10.0));
        assert!((b.size().y - 5.0).abs() < 1e-9);
        assert!((b.ne().lat - LAT_MAX).abs() < 1e-6);
    }

    #[test]
    fn default_is_valid() {
        let b = Wgs84Aabb::default();
        assert_eq!(b.sw(), Wgs84::new(0.0, 0.0));
        assert_eq!(b.size(), Vec2::new(0.0, 0.0));
        assert!(b.valid());
    }

    #[test]
    fn from_tile_level10_origin() {
        let tile = PackedTileId::from_tile_index(0, 10).unwrap();
        let b = Wgs84Aabb::from_tile(&tile);
        assert!((b.sw().lon - 0.0).abs() < 1e-9);
        assert!((b.sw().lat - 0.0).abs() < 1e-9);
        assert!((b.size().x - 0.17578125).abs() < 1e-9);
        assert!((b.size().y - 0.17578125).abs() < 1e-9);
        assert!(b.valid());
    }

    #[test]
    fn invalid_neg_size_keeps_size() {
        let b = Wgs84Aabb::new(Wgs84::new(0.0, 85.0), Vec2::new(-1.0, 10.0));
        assert!(!b.valid());
        // Size stored unmodified (no clamp applied).
        assert_eq!(b.size(), Vec2::new(-1.0, 10.0));
    }

    #[test]
    fn from_center_and_tile_limit_basic() {
        let b = Wgs84Aabb::from_center_and_tile_limit(Wgs84::new(10.0, 20.0), 16, 5);
        assert!(b.valid());
        // Center should be near the requested center.
        assert!((b.center().lon - 10.0).abs() < 1.0);
    }

    #[test]
    fn avg_mercator_stretch_is_finite() {
        let b = Wgs84Aabb::new(Wgs84::new(0.0, 10.0), Vec2::new(20.0, 10.0));
        assert!(b.avg_mercator_stretch().is_finite());
    }

    #[test]
    fn antimeridian_split() {
        let b = Wgs84Aabb::new(Wgs84::new(175.0, 0.0), Vec2::new(10.0, 5.0));
        assert!(b.contains_anti_meridian());
        let (left, right) = b.split_over_anti_meridian().unwrap();
        assert!((left.sw().lon - 175.0).abs() < 1e-9);
        assert!((left.size().x - 4.999999916180968).abs() < 1e-6);
        assert!((right.sw().lon - (-180.0)).abs() < 1e-9);
        assert!((right.size().x - 5.000000083819032).abs() < 1e-6);

        // A box not past LON_MAX returns None.
        let small = Wgs84Aabb::new(Wgs84::new(0.0, 0.0), Vec2::new(10.0, 5.0));
        assert!(!small.contains_anti_meridian());
        assert!(small.split_over_anti_meridian().is_none());
    }
}
