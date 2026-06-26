// SPDX-License-Identifier: BSD-3-Clause
//! Generic polygon container with orientation, mirroring the C++ `Polygon`.
//!
//! Port of `cpp/include/ndsmath/polygon.h` and the Python reference
//! `python/src/ndslive/math/polygon.py`. The C++ class is a template over a
//! vertex container; here it is specialized directly to a `Vec` of
//! [`crate::Wgs84`] vertices. Orientation is computed on the raw `(lon, lat)`
//! plane (no WGS84 normalization, no antimeridian handling).

use crate::wgs84::Wgs84;

/// Winding order of a polygon. Integer values match the C++ enum.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(i8)]
pub enum Orientation {
    /// Clockwise winding (negative signed area).
    Clockwise = -1,
    /// Degenerate / unsupported polygon (zero area or unsupported type).
    InvalidOrientation = 0,
    /// Counter-clockwise winding (positive signed area).
    CounterClockwise = 1,
}

/// Polygon topology. Integer values match the C++ enum.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum PolygonType {
    /// A simple polygon with an arbitrary number of vertices and no holes; the
    /// last vertex connects back to the first.
    SimplePolygon = 0,
    /// A triangle strip.
    TriangleStrip = 1,
    /// A triangle fan.
    TriangleFan = 2,
    /// A set of independent triangles; three consecutive vertices form one.
    TriangleList = 3,
    /// Illegal polygon type, used to signal failure.
    Unknown = 4,
}

/// A set of vertices with a topology type and orientation query.
///
/// Mirrors the C++ `Polygon<Vector>` template. The base [`Polygon::is_valid`]
/// requires at least one vertex; [`crate::Wgs84Polygon`] wraps this and
/// overrides validity to require at least three.
#[derive(Debug, Clone, PartialEq)]
pub struct Polygon {
    polygon_type: PolygonType,
    vertices: Vec<Wgs84>,
}

impl Polygon {
    /// Construct an empty polygon of the given type.
    pub fn new(polygon_type: PolygonType) -> Self {
        Polygon {
            polygon_type,
            vertices: Vec::new(),
        }
    }

    /// Construct a polygon of the given type with the supplied vertices.
    pub fn with_vertices(polygon_type: PolygonType, vertices: Vec<Wgs84>) -> Self {
        Polygon {
            polygon_type,
            vertices,
        }
    }

    /// Append a single vertex.
    pub fn add_vertex(&mut self, position: Wgs84) {
        self.vertices.push(position);
    }

    /// Append a list of vertices, in order.
    pub fn add_vertices(&mut self, vertices: &[Wgs84]) {
        self.vertices.extend_from_slice(vertices);
    }

    /// Get a vertex by index (panics on out-of-bounds, like C++ `operator[]`).
    pub fn get(&self, index: usize) -> Wgs84 {
        self.vertices[index]
    }

    /// Set a vertex by index.
    pub fn set(&mut self, index: usize, value: Wgs84) {
        self.vertices[index] = value;
    }

    /// Number of vertices.
    pub fn len(&self) -> usize {
        self.vertices.len()
    }

    /// Whether the polygon has no vertices.
    pub fn is_empty(&self) -> bool {
        self.vertices.is_empty()
    }

    /// Get the polygon type.
    pub fn polygon_type(&self) -> PolygonType {
        self.polygon_type
    }

    /// Set the polygon type.
    pub fn set_type(&mut self, polygon_type: PolygonType) {
        self.polygon_type = polygon_type;
    }

    /// Whether this is a valid polygon.
    ///
    /// Base implementation: at least one vertex. [`crate::Wgs84Polygon`]
    /// requires at least three.
    pub fn is_valid(&self) -> bool {
        !self.vertices.is_empty()
    }

    /// Get the (shared) slice of vertices.
    pub fn vertices(&self) -> &[Wgs84] {
        &self.vertices
    }

    /// Get the mutable `Vec` of vertices.
    pub fn vertices_mut(&mut self) -> &mut Vec<Wgs84> {
        &mut self.vertices
    }

    /// Compute the winding order via the signed shoelace formula.
    ///
    /// Only works for `SimplePolygon` and a single-triangle `TriangleList`
    /// (exactly 3 vertices). All other types return `InvalidOrientation`
    /// without computing area. Collinear vertices (zero area) also return
    /// `InvalidOrientation`.
    ///
    /// Uses raw `(lon, lat)` doubles; no normalization.
    pub fn orientation(&self) -> Orientation {
        let is_supported = self.polygon_type == PolygonType::SimplePolygon
            || (self.polygon_type == PolygonType::TriangleList && self.vertices.len() == 3);
        if !is_supported {
            return Orientation::InvalidOrientation;
        }

        let n = self.vertices.len();
        let mut area = 0.0_f64;
        for i in 0..n {
            let j = if i + 1 == n { 0 } else { i + 1 };
            area += self.vertices[i].lon * self.vertices[j].lat;
            area -= self.vertices[i].lat * self.vertices[j].lon;
        }

        if area > 0.0 {
            Orientation::CounterClockwise
        } else if area < 0.0 {
            Orientation::Clockwise
        } else {
            Orientation::InvalidOrientation
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn pts(coords: &[(f64, f64)]) -> Vec<Wgs84> {
        coords.iter().map(|&(x, y)| Wgs84::new(x, y)).collect()
    }

    #[test]
    fn base_is_valid_needs_one_vertex() {
        let empty = Polygon::new(PolygonType::SimplePolygon);
        assert!(!empty.is_valid());
        assert!(empty.is_empty());
        let mut one = Polygon::new(PolygonType::SimplePolygon);
        one.add_vertex(Wgs84::new(0.0, 0.0));
        assert!(one.is_valid());
    }

    #[test]
    fn ccw_and_cw() {
        let ccw = Polygon::with_vertices(
            PolygonType::SimplePolygon,
            pts(&[(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]),
        );
        assert_eq!(ccw.orientation(), Orientation::CounterClockwise);

        let cw = Polygon::with_vertices(
            PolygonType::SimplePolygon,
            pts(&[(0.0, 0.0), (0.0, 1.0), (1.0, 0.0)]),
        );
        assert_eq!(cw.orientation(), Orientation::Clockwise);
    }

    #[test]
    fn collinear_is_invalid() {
        let p = Polygon::with_vertices(
            PolygonType::SimplePolygon,
            pts(&[(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)]),
        );
        assert_eq!(p.orientation(), Orientation::InvalidOrientation);
    }

    #[test]
    fn unsupported_type_is_invalid() {
        let strip = Polygon::with_vertices(
            PolygonType::TriangleStrip,
            pts(&[(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]),
        );
        assert_eq!(strip.orientation(), Orientation::InvalidOrientation);

        // A multi-triangle TRIANGLE_LIST (4 vertices) is also unsupported.
        let multi = Polygon::with_vertices(
            PolygonType::TriangleList,
            pts(&[(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)]),
        );
        assert_eq!(multi.orientation(), Orientation::InvalidOrientation);
    }

    #[test]
    fn single_triangle_list_allowed() {
        let t = Polygon::with_vertices(
            PolygonType::TriangleList,
            pts(&[(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]),
        );
        assert_eq!(t.orientation(), Orientation::CounterClockwise);
    }

    #[test]
    fn get_set_and_accessors() {
        let mut p = Polygon::new(PolygonType::Unknown);
        p.add_vertices(&pts(&[(1.0, 2.0), (3.0, 4.0)]));
        assert_eq!(p.len(), 2);
        assert_eq!(p.polygon_type(), PolygonType::Unknown);
        assert_eq!(p.get(0), Wgs84::new(1.0, 2.0));
        p.set(0, Wgs84::new(5.0, 6.0));
        assert_eq!(p.get(0), Wgs84::new(5.0, 6.0));
        p.set_type(PolygonType::SimplePolygon);
        assert_eq!(p.polygon_type(), PolygonType::SimplePolygon);
        assert_eq!(p.vertices().len(), 2);
        p.vertices_mut().push(Wgs84::new(7.0, 8.0));
        assert_eq!(p.len(), 3);
    }
}
