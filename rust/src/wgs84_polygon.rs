// SPDX-License-Identifier: BSD-3-Clause
//! WGS84 polygon with bounding box, median, and SAT collision.
//!
//! Port of the C++ `HighPrecWgs84Polygon`
//! (`cpp/include/ndsmath/wgs84polygon.h`) and the Python reference
//! `python/src/ndslive/math/wgs84_polygon.py`. A [`Polygon`] of [`Wgs84`]
//! vertices, defaulting to `SimplePolygon`, with:
//!
//! * [`Wgs84Polygon::aa_bb`] — the axis-aligned bounding box,
//! * [`Wgs84Polygon::median`] — the centroid (with a *deliberately preserved*
//!   lon/lat swap quirk from the C++ reference),
//! * [`Wgs84Polygon::collides_with`] — Separating-Axis-Theorem collision.
//!
//! The collision math runs on raw `(lon, lat)` doubles: no normalization, no
//! antimeridian handling.

use crate::polygon::{Polygon, PolygonType};
use crate::vec2::Vec2;
use crate::wgs84::Wgs84;
use crate::wgs84_aabb::Wgs84Aabb;

/// A simple polygon of WGS84 vertices with collision and bbox helpers.
///
/// Wraps a [`Polygon`] (default type `SimplePolygon`) and overrides validity to
/// require at least three vertices.
#[derive(Debug, Clone)]
pub struct Wgs84Polygon {
    inner: Polygon,
}

impl Wgs84Polygon {
    /// Construct an empty simple polygon.
    pub fn new() -> Self {
        Wgs84Polygon {
            inner: Polygon::new(PolygonType::SimplePolygon),
        }
    }

    /// Construct a simple polygon with the supplied vertices.
    pub fn from_vertices(vertices: Vec<Wgs84>) -> Self {
        Wgs84Polygon {
            inner: Polygon::with_vertices(PolygonType::SimplePolygon, vertices),
        }
    }

    /// Construct an empty polygon of the given type.
    pub fn with_type(polygon_type: PolygonType) -> Self {
        Wgs84Polygon {
            inner: Polygon::new(polygon_type),
        }
    }

    /// Construct a polygon of the given type with the supplied vertices.
    pub fn with_type_and_vertices(polygon_type: PolygonType, vertices: Vec<Wgs84>) -> Self {
        Wgs84Polygon {
            inner: Polygon::with_vertices(polygon_type, vertices),
        }
    }

    /// The 4-vertex sentinel polygon wrapping the whole Earth.
    ///
    /// Constructed from `(-180,-90), (-180,90), (180,-90), (180,90)`. These
    /// coordinates pass through [`Wgs84`] normalization, so the stored values
    /// are not exactly those literals. This polygon is only used as an identity
    /// sentinel in [`Wgs84Polygon::collides_with`] via `==`; its exact
    /// normalized coordinates are not part of cross-language parity.
    pub fn earth_wrapping_poly() -> Wgs84Polygon {
        Wgs84Polygon::from_vertices(vec![
            Wgs84::new(-180.0, -90.0),
            Wgs84::new(-180.0, 90.0),
            Wgs84::new(180.0, -90.0),
            Wgs84::new(180.0, 90.0),
        ])
    }

    /// Append a single vertex.
    pub fn add_vertex(&mut self, position: Wgs84) {
        self.inner.add_vertex(position);
    }

    /// Append a list of vertices, in order.
    pub fn add_vertices(&mut self, vertices: &[Wgs84]) {
        self.inner.add_vertices(vertices);
    }

    /// Get a vertex by index.
    pub fn get(&self, index: usize) -> Wgs84 {
        self.inner.get(index)
    }

    /// Number of vertices.
    pub fn len(&self) -> usize {
        self.inner.len()
    }

    /// Whether the polygon has no vertices.
    pub fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }

    /// The polygon type.
    pub fn polygon_type(&self) -> PolygonType {
        self.inner.polygon_type()
    }

    /// The shared slice of vertices.
    pub fn vertices(&self) -> &[Wgs84] {
        self.inner.vertices()
    }

    /// Compute the winding order (see [`Polygon::orientation`]).
    pub fn orientation(&self) -> crate::polygon::Orientation {
        self.inner.orientation()
    }

    /// Whether this is a valid polygon: at least 3 vertices.
    pub fn is_valid(&self) -> bool {
        self.inner.len() >= 3
    }

    /// Order-sensitive vertex-wise equality (via [`Wgs84`] approximate `==`).
    pub fn equals(&self, other: &Wgs84Polygon) -> bool {
        let v = self.inner.vertices();
        let vo = other.inner.vertices();
        if v.len() != vo.len() {
            return false;
        }
        v.iter().zip(vo.iter()).all(|(a, b)| a == b)
    }

    /// The axis-aligned bounding box of this polygon.
    ///
    /// Returns a default (empty) [`Wgs84Aabb`] if the polygon is invalid (fewer
    /// than 3 vertices). The size is computed as raw coordinate differences
    /// (not normalized), then handed to the [`Wgs84Aabb`] constructor, which
    /// still applies the excess-height clamp.
    pub fn aa_bb(&self) -> Wgs84Aabb {
        if !self.is_valid() {
            return Wgs84Aabb::default();
        }

        let vs = self.inner.vertices();
        let mut min_lon = vs[0].lon;
        let mut max_lon = vs[0].lon;
        let mut min_lat = vs[0].lat;
        let mut max_lat = vs[0].lat;
        for v in &vs[1..] {
            min_lon = min_lon.min(v.lon);
            max_lon = max_lon.max(v.lon);
            min_lat = min_lat.min(v.lat);
            max_lat = max_lat.max(v.lat);
        }

        Wgs84Aabb::new(
            Wgs84::new(min_lon, min_lat),
            Vec2::new(max_lon - min_lon, max_lat - min_lat),
        )
    }

    /// The centroid of the polygon vertices.
    ///
    /// # Warning
    ///
    /// This faithfully reproduces a bug in the C++ reference. The C++
    /// `median()` returns `HighPrecWgs84(medLat, medLon)` while the
    /// `Wgs84(longitude, latitude)` constructor takes longitude first — so the
    /// **mean latitude is stored in the longitude slot and the mean longitude
    /// in the latitude slot**. The returned point therefore has
    /// `lon == mean_lat` and `lat == mean_lon`. For symmetric polygons the swap
    /// is invisible; for asymmetric ones it is observable. It is preserved here
    /// for cross-language parity.
    ///
    /// The means are accumulated as `sum(coord / n)` per the C++ code (not
    /// `sum(coord) / n`), to match its floating-point rounding.
    pub fn median(&self) -> Wgs84 {
        let vs = self.inner.vertices();
        let n = vs.len() as f64;
        let mut med_lat = 0.0_f64;
        for p in vs {
            med_lat += p.lat / n;
        }
        let mut med_lon = 0.0_f64;
        for p in vs {
            med_lon += p.lon / n;
        }
        // NOTE: lon/lat swap preserved from the C++ reference (see docs).
        Wgs84::new(med_lat, med_lon)
    }

    /// Whether this polygon collides with `other` (Separating-Axis Theorem).
    ///
    /// The earth-wrapping sentinel collides with everything. Otherwise the SAT
    /// axis sets are taken from this polygon's edges (first test) and from
    /// `other`'s edges (second test); if no separating axis is found on either,
    /// the polygons collide.
    pub fn collides_with(&self, other: &Wgs84Polygon) -> bool {
        let earth = Wgs84Polygon::earth_wrapping_poly();
        if self.equals(&earth) || other.equals(&earth) {
            return true;
        }
        if Self::are_separate(self, other, self) {
            return false;
        }
        // NOTE: the C++ reference passes (other, other) here — axes come from
        // `other`'s edges, projecting both `self` and `other`. Preserved exactly.
        if Self::are_separate(self, other, other) {
            return false;
        }
        true
    }

    /// Project `poly` onto `axis`, returning `(min, max)`.
    fn project_on_axis(poly: &Wgs84Polygon, axis: Vec2) -> (f64, f64) {
        let mut minimum = f64::INFINITY;
        let mut maximum = f64::NEG_INFINITY;

        let vs = poly.inner.vertices();
        let n = vs.len();
        for i in 0..n {
            let ni = if i + 1 == n { 0 } else { i + 1 };
            let (beg_x, beg_y) = (vs[i].lon, vs[i].lat);
            let (end_x, end_y) = (vs[ni].lon, vs[ni].lat);

            let x0 = beg_x * axis.x + beg_y * axis.y;
            minimum = minimum.min(x0);
            maximum = maximum.max(x0);

            let x1 = x0 + (end_x - beg_x) * axis.x + (end_y - beg_y) * axis.y;
            minimum = minimum.min(x1);
            maximum = maximum.max(x1);
        }

        (minimum, maximum)
    }

    /// Whether two 1D intervals `(min, max)` are disjoint.
    fn are_separate_1d(min_max1: (f64, f64), min_max2: (f64, f64)) -> bool {
        (min_max1.0 < min_max2.0 && min_max1.1 < min_max2.0)
            || (min_max1.0 > min_max2.1 && min_max1.1 > min_max2.1)
    }

    /// Whether a separating axis exists among `ref_for_axis`'s edge normals.
    fn are_separate(
        this: &Wgs84Polygon,
        other: &Wgs84Polygon,
        ref_for_axis: &Wgs84Polygon,
    ) -> bool {
        let vs = ref_for_axis.inner.vertices();
        let n = vs.len();
        for i in 0..n {
            let ni = if i + 1 == n { 0 } else { i + 1 };
            let dx = vs[ni].lon - vs[i].lon;
            let dy = vs[ni].lat - vs[i].lat;
            let normal = Vec2::new(dy, -dx);

            let min_max_poly1 = Self::project_on_axis(this, normal);
            let min_max_poly2 = Self::project_on_axis(other, normal);

            if Self::are_separate_1d(min_max_poly1, min_max_poly2) {
                return true;
            }
        }
        false
    }
}

impl Default for Wgs84Polygon {
    fn default() -> Self {
        Wgs84Polygon::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn pts(coords: &[(f64, f64)]) -> Vec<Wgs84> {
        coords.iter().map(|&(x, y)| Wgs84::new(x, y)).collect()
    }

    #[test]
    fn validity_and_constructors() {
        assert!(Wgs84Polygon::new().is_empty());
        assert_eq!(
            Wgs84Polygon::new().polygon_type(),
            PolygonType::SimplePolygon
        );
        let two = Wgs84Polygon::from_vertices(pts(&[(0.0, 0.0), (1.0, 0.0)]));
        assert!(!two.is_valid());
        let three = Wgs84Polygon::from_vertices(pts(&[(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]));
        assert!(three.is_valid());
        assert_eq!(three.len(), 3);
        assert_eq!(three.get(1), Wgs84::new(1.0, 0.0));

        let typed = Wgs84Polygon::with_type(PolygonType::TriangleList);
        assert_eq!(typed.polygon_type(), PolygonType::TriangleList);
        let typed_v = Wgs84Polygon::with_type_and_vertices(
            PolygonType::TriangleList,
            pts(&[(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]),
        );
        assert_eq!(
            typed_v.orientation(),
            crate::polygon::Orientation::CounterClockwise
        );
    }

    #[test]
    fn add_vertex_and_vertices() {
        let mut p = Wgs84Polygon::new();
        p.add_vertex(Wgs84::new(0.0, 0.0));
        p.add_vertices(&pts(&[(1.0, 0.0), (0.0, 1.0)]));
        assert_eq!(p.len(), 3);
        assert_eq!(p.vertices().len(), 3);
    }

    #[test]
    fn aa_bb_valid_and_invalid() {
        let tri = Wgs84Polygon::from_vertices(pts(&[(0.0, 0.0), (4.0, 0.0), (0.0, 4.0)]));
        let bb = tri.aa_bb();
        assert_eq!(bb.sw(), Wgs84::new(0.0, 0.0));
        assert_eq!(bb.size(), Vec2::new(4.0, 4.0));

        let invalid = Wgs84Polygon::from_vertices(pts(&[(0.0, 0.0), (1.0, 0.0)]));
        let dbb = invalid.aa_bb();
        assert_eq!(dbb.sw(), Wgs84::new(0.0, 0.0));
        assert_eq!(dbb.size(), Vec2::new(0.0, 0.0));
    }

    #[test]
    fn median_swap_quirk() {
        // Asymmetric triangle: mean_lon = 10, mean_lat = 20, but the result
        // swaps them: lon == 20, lat == 10.
        let tri = Wgs84Polygon::from_vertices(pts(&[(0.0, 0.0), (30.0, 0.0), (0.0, 60.0)]));
        let m = tri.median();
        assert!((m.lon - 20.0).abs() < 1e-9);
        assert!((m.lat - 10.0).abs() < 1e-9);
    }

    #[test]
    fn collision_cases() {
        let tri = Wgs84Polygon::from_vertices(pts(&[(0.0, 0.0), (4.0, 0.0), (0.0, 4.0)]));
        let overlap = Wgs84Polygon::from_vertices(pts(&[(1.0, 1.0), (5.0, 1.0), (1.0, 5.0)]));
        let disjoint =
            Wgs84Polygon::from_vertices(pts(&[(20.0, 20.0), (24.0, 20.0), (20.0, 24.0)]));
        let earth = Wgs84Polygon::earth_wrapping_poly();

        assert!(tri.collides_with(&overlap));
        assert!(overlap.collides_with(&tri));
        assert!(!tri.collides_with(&disjoint));
        assert!(!disjoint.collides_with(&tri));
        assert!(tri.collides_with(&earth));
        assert!(earth.collides_with(&tri));
        assert!(tri.collides_with(&tri));
    }

    #[test]
    fn equals_order_and_length() {
        let a = Wgs84Polygon::from_vertices(pts(&[(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]));
        let b = Wgs84Polygon::from_vertices(pts(&[(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]));
        let c = Wgs84Polygon::from_vertices(pts(&[(0.0, 0.0), (0.0, 1.0), (1.0, 0.0)]));
        let short = Wgs84Polygon::from_vertices(pts(&[(0.0, 0.0), (1.0, 0.0)]));
        assert!(a.equals(&b));
        assert!(!a.equals(&c));
        assert!(!a.equals(&short));
    }

    #[test]
    fn collision_separated_by_other_axes() {
        // A diamond whose own edge normals do NOT separate it from `box`, but
        // `box`'s axis-aligned normals do. This exercises the second
        // `are_separate(self, other, other)` call in `collides_with`.
        let diamond =
            Wgs84Polygon::from_vertices(pts(&[(0.0, 2.0), (2.0, 0.0), (0.0, -2.0), (-2.0, 0.0)]));
        let boxp =
            Wgs84Polygon::from_vertices(pts(&[(3.0, -1.0), (5.0, -1.0), (5.0, 1.0), (3.0, 1.0)]));
        assert!(!diamond.collides_with(&boxp));
        assert!(!boxp.collides_with(&diamond));
    }

    #[test]
    fn default_is_empty_simple_polygon() {
        let p = Wgs84Polygon::default();
        assert!(p.is_empty());
        assert_eq!(p.polygon_type(), PolygonType::SimplePolygon);
    }
}
