// SPDX-License-Identifier: BSD-3-Clause
//! Ear-clipping polygon triangulation.
//!
//! Port of the C++ `PolygonTriangulation`
//! (`cpp/include/ndsmath/polygontriangulation.{h,cpp}`) and the Python
//! reference `python/src/ndslive/math/triangulation.py`. The C++ implementation
//! uses a pointer-linked ring of partition vertices; this port uses an
//! index-linked `Vec` of [`PartitionVertex`] (`previous` / `next` integer
//! indices) to avoid manual memory management while reproducing the same
//! traversal.
//!
//! # Note
//!
//! The *set* of output triangles is deterministic, but the ordering of
//! triangles and the rotation of each triangle's three vertices are
//! implementation-specific (driven by the "most extruded ear" tie-break and
//! floating-point `angle` comparisons). Triangulation output is therefore
//! **not** part of the cross-language parity vectors; tests assert structure
//! (type and vertex count) only.

use crate::polygon::PolygonType;
use crate::wgs84::Wgs84;
use crate::wgs84_polygon::Wgs84Polygon;

/// A node in the ear-clipping ring (index-linked replacement for pointers).
#[derive(Debug, Clone, Copy)]
struct PartitionVertex {
    is_active: bool,
    is_convex: bool,
    is_ear: bool,
    p: Wgs84,
    angle: f64,
    previous: usize,
    next: usize,
}

/// Triangulates simple polygons by ear clipping (O(n^2)).
#[derive(Debug, Default, Clone, Copy)]
pub struct PolygonTriangulation;

impl PolygonTriangulation {
    /// Construct a new triangulator.
    pub fn new() -> Self {
        PolygonTriangulation
    }

    /// Triangulate a CCW simple polygon into a `TriangleList`.
    ///
    /// The input must be a `SimplePolygon` with at least 3 vertices, in
    /// counter-clockwise order. Returns a [`Wgs84Polygon`] of type
    /// `TriangleList` on success (`3 * (n - 2)` vertices), or a polygon of type
    /// `Unknown` on failure (wrong type, too few vertices, or no ear found).
    pub fn triangulate_by_ear_clipping(&self, polygon: &Wgs84Polygon) -> Wgs84Polygon {
        let mut result = Wgs84Polygon::with_type(PolygonType::TriangleList);

        if polygon.polygon_type() != PolygonType::SimplePolygon || polygon.vertices().len() < 3 {
            return Wgs84Polygon::with_type(PolygonType::Unknown);
        }

        let num_vertices = polygon.vertices().len();

        // Nothing to do for a single triangle.
        if num_vertices == 3 {
            result.add_vertices(polygon.vertices());
            return result;
        }

        let mut vertices: Vec<PartitionVertex> = (0..num_vertices)
            .map(|i| PartitionVertex {
                is_active: true,
                is_convex: false,
                is_ear: false,
                p: polygon.get(i),
                angle: 0.0,
                next: if i == num_vertices - 1 { 0 } else { i + 1 },
                previous: if i == 0 { num_vertices - 1 } else { i - 1 },
            })
            .collect();

        for i in 0..num_vertices {
            Self::update_vertex(i, &mut vertices, num_vertices);
        }

        let mut ear = 0usize;
        for i in 0..(num_vertices - 3) {
            let mut ear_found = false;

            // Find the most extruded ear (largest angle; first wins ties).
            for j in 0..num_vertices {
                if !vertices[j].is_active || !vertices[j].is_ear {
                    continue;
                }
                if !ear_found {
                    ear_found = true;
                    ear = j;
                } else if vertices[j].angle > vertices[ear].angle {
                    ear = j;
                }
            }

            if !ear_found {
                return Wgs84Polygon::with_type(PolygonType::Unknown);
            }

            let ear_prev = vertices[ear].previous;
            let ear_next = vertices[ear].next;
            result.add_vertex(vertices[ear_prev].p);
            result.add_vertex(vertices[ear].p);
            result.add_vertex(vertices[ear_next].p);

            vertices[ear].is_active = false;
            vertices[ear_prev].next = ear_next;
            vertices[ear_next].previous = ear_prev;

            if i == num_vertices - 4 {
                break;
            }

            Self::update_vertex(ear_prev, &mut vertices, num_vertices);
            Self::update_vertex(ear_next, &mut vertices, num_vertices);
        }

        for i in 0..num_vertices {
            if vertices[i].is_active {
                let prev = vertices[i].previous;
                let next = vertices[i].next;
                result.add_vertex(vertices[prev].p);
                result.add_vertex(vertices[i].p);
                result.add_vertex(vertices[next].p);
                break;
            }
        }

        result
    }

    /// Vector-normalize `p`; `(0, 0)` if it has zero length.
    ///
    /// Mirrors the C++ `normalize`: the unit vector is wrapped back into a
    /// [`Wgs84`] (which re-normalizes as a coordinate). Odd, but part of the
    /// reference behavior.
    fn normalize(p: Wgs84) -> Wgs84 {
        let n = (p.lon * p.lon + p.lat * p.lat).sqrt();
        if n != 0.0 {
            Wgs84::new(p.lon / n, p.lat / n)
        } else {
            Wgs84::new(0.0, 0.0)
        }
    }

    /// Whether the turn `p1 -> p2 -> p3` is convex (positive cross product).
    fn is_convex(p1: Wgs84, p2: Wgs84, p3: Wgs84) -> bool {
        (p3.lat - p1.lat) * (p2.lon - p1.lon) - (p3.lon - p1.lon) * (p2.lat - p1.lat) > 0.0
    }

    /// Whether point `p` lies inside triangle `(p1, p2, p3)`.
    fn is_inside(p1: Wgs84, p2: Wgs84, p3: Wgs84, p: Wgs84) -> bool {
        !Self::is_convex(p1, p, p2) && !Self::is_convex(p2, p, p3) && !Self::is_convex(p3, p, p1)
    }

    /// Recompute convexity, ear status, and angle of vertex `v_idx`.
    fn update_vertex(v_idx: usize, vertices: &mut [PartitionVertex], num_vertices: usize) {
        let prev_idx = vertices[v_idx].previous;
        let next_idx = vertices[v_idx].next;
        let v_p = vertices[v_idx].p;
        let v1_p = vertices[prev_idx].p;
        let v3_p = vertices[next_idx].p;

        let is_convex = Self::is_convex(v1_p, v_p, v3_p);

        // NOTE: the subtraction goes through Wgs84 `operator-` which
        // re-normalizes, matching the reference exactly.
        let vec1 = Self::normalize(v1_p - v_p);
        let vec3 = Self::normalize(v3_p - v_p);

        let angle = vec1.lon * vec3.lon + vec1.lat * vec3.lat;

        let mut is_ear = false;
        if is_convex {
            is_ear = true;
            for vert in vertices.iter().take(num_vertices) {
                let ip = vert.p;
                if ip.lon == v_p.lon && ip.lat == v_p.lat {
                    continue;
                }
                if ip.lon == v1_p.lon && ip.lat == v1_p.lat {
                    continue;
                }
                if ip.lon == v3_p.lon && ip.lat == v3_p.lat {
                    continue;
                }
                if Self::is_inside(v1_p, v_p, v3_p, ip) {
                    is_ear = false;
                    break;
                }
            }
        }

        let v = &mut vertices[v_idx];
        v.is_convex = is_convex;
        v.angle = angle;
        v.is_ear = is_ear;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn pts(coords: &[(f64, f64)]) -> Vec<Wgs84> {
        coords.iter().map(|&(x, y)| Wgs84::new(x, y)).collect()
    }

    #[test]
    fn triangle_passthrough() {
        let t = PolygonTriangulation::new();
        let poly = Wgs84Polygon::from_vertices(pts(&[(0.0, 0.0), (4.0, 0.0), (0.0, 4.0)]));
        let out = t.triangulate_by_ear_clipping(&poly);
        assert_eq!(out.polygon_type(), PolygonType::TriangleList);
        assert_eq!(out.vertices().len(), 3);
    }

    #[test]
    fn convex_quad() {
        let t = PolygonTriangulation;
        let poly =
            Wgs84Polygon::from_vertices(pts(&[(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)]));
        let out = t.triangulate_by_ear_clipping(&poly);
        assert_eq!(out.polygon_type(), PolygonType::TriangleList);
        // 3 * (n - 2) == 3 * 2 == 6 for a quad.
        assert_eq!(out.vertices().len(), 6);
    }

    #[test]
    fn concave_with_reflex_vertex() {
        let t = PolygonTriangulation::new();
        // An arrow / "dart" shape: the vertex (2, 2) is reflex (CCW order).
        let poly = Wgs84Polygon::from_vertices(pts(&[
            (0.0, 0.0),
            (4.0, 0.0),
            (2.0, 2.0),
            (4.0, 4.0),
            (0.0, 4.0),
        ]));
        let out = t.triangulate_by_ear_clipping(&poly);
        assert_eq!(out.polygon_type(), PolygonType::TriangleList);
        // 3 * (5 - 2) == 9.
        assert_eq!(out.vertices().len(), 9);
    }

    #[test]
    fn too_few_vertices_is_unknown() {
        let t = PolygonTriangulation::new();
        let poly = Wgs84Polygon::from_vertices(pts(&[(0.0, 0.0), (1.0, 0.0)]));
        let out = t.triangulate_by_ear_clipping(&poly);
        assert_eq!(out.polygon_type(), PolygonType::Unknown);
        assert!(out.is_empty());
    }

    #[test]
    fn wrong_type_is_unknown() {
        let t = PolygonTriangulation::new();
        let poly = Wgs84Polygon::with_type_and_vertices(
            PolygonType::TriangleList,
            pts(&[(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)]),
        );
        let out = t.triangulate_by_ear_clipping(&poly);
        assert_eq!(out.polygon_type(), PolygonType::Unknown);
    }

    #[test]
    fn regular_pentagon_uses_angle_tiebreak() {
        // A regular pentagon's ears have differing angles, so the "most
        // extruded ear" tie-break (largest angle wins) is exercised.
        let t = PolygonTriangulation::new();
        let mut coords = Vec::new();
        for i in 0..5 {
            let a = 2.0 * std::f64::consts::PI * (i as f64) / 5.0;
            coords.push((a.cos(), a.sin()));
        }
        let poly = Wgs84Polygon::from_vertices(pts(&coords));
        let out = t.triangulate_by_ear_clipping(&poly);
        assert_eq!(out.polygon_type(), PolygonType::TriangleList);
        // 3 * (5 - 2) == 9.
        assert_eq!(out.vertices().len(), 9);
    }

    #[test]
    fn clockwise_polygon_finds_no_ear() {
        // A clockwise (wrong-winding) quad has no convex ears, so ear clipping
        // fails and returns an UNKNOWN polygon.
        let t = PolygonTriangulation::new();
        let poly =
            Wgs84Polygon::from_vertices(pts(&[(0.0, 0.0), (0.0, 4.0), (4.0, 4.0), (4.0, 0.0)]));
        let out = t.triangulate_by_ear_clipping(&poly);
        assert_eq!(out.polygon_type(), PolygonType::Unknown);
        assert!(out.is_empty());
    }

    #[test]
    fn coincident_vertex_zero_length_edge() {
        // A duplicated leading vertex creates a zero-length edge, exercising the
        // `normalize` zero-length branch. Still triangulates into 3*(n-2) verts.
        let t = PolygonTriangulation::new();
        let poly =
            Wgs84Polygon::from_vertices(pts(&[(0.0, 0.0), (0.0, 0.0), (4.0, 0.0), (0.0, 4.0)]));
        let out = t.triangulate_by_ear_clipping(&poly);
        assert_eq!(out.polygon_type(), PolygonType::TriangleList);
        assert_eq!(out.vertices().len(), 6);
    }
}
