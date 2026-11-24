// SPDX-License-Identifier: BSD-3-Clause
//! Closed polygon/rectangle intersection in raw coordinates, with open hole interiors.
use crate::Vec2;

/// Relation of a closed rectangle to a valid polygon with holes.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum PolygonAreaRelation {
    Outside = 0,
    Inside = 1,
    Boundary = 2,
}
/// Ignore one repeated closing vertex.
fn size(r: &[Vec2]) -> usize {
    if r.len() > 1 && r.first() == r.last() {
        r.len() - 1
    } else {
        r.len()
    }
}
/// Exact low/high difference components.
fn difference(a: f64, b: f64) -> [f64; 2] {
    let high = a - b;
    let virtual_b = a - high;
    [(a - (high + virtual_b)) + (virtual_b - b), high]
}
/// Add a scalar to a nonoverlapping expansion without losing bits.
fn grow(expansion: &mut Vec<f64>, mut value: f64) {
    let mut count = 0;
    for i in 0..expansion.len() {
        let term = expansion[i];
        let total = value + term;
        let virtual_term = total - value;
        let low = (value - (total - virtual_term)) + (term - virtual_term);
        if low != 0.0 {
            expansion[count] = low;
            count += 1;
        }
        value = total;
    }
    expansion.truncate(count);
    if value != 0.0 {
        expansion.push(value);
    }
}
/// Orientation sign with an exact expansion fallback for ambiguous determinants.
fn cross(a: Vec2, b: Vec2, c: Vec2) -> f64 {
    let left = (b.x - a.x) * (c.y - a.y);
    let right = (b.y - a.y) * (c.x - a.x);
    let determinant = left - right;
    if determinant.abs() > (left.abs() + right.abs()) * 8.0 * f64::EPSILON {
        return determinant;
    }
    let mut expansion = Vec::with_capacity(16);
    for sign in [1.0, -1.0] {
        let x = if sign > 0.0 {
            difference(b.x, a.x)
        } else {
            difference(b.y, a.y)
        };
        let y = if sign > 0.0 {
            difference(c.y, a.y)
        } else {
            difference(c.x, a.x)
        };
        for u in x {
            for v in y {
                let high = u * v;
                grow(&mut expansion, sign * u.mul_add(v, -high));
                grow(&mut expansion, sign * high);
            }
        }
    }
    expansion.last().copied().unwrap_or(0.0)
}
/// Closed segment membership.
fn on(p: Vec2, a: Vec2, b: Vec2) -> bool {
    cross(a, b, p) == 0.0
        && p.x >= a.x.min(b.x)
        && p.x <= a.x.max(b.x)
        && p.y >= a.y.min(b.y)
        && p.y <= a.y.max(b.y)
}
/// Closed segment intersection, including collinear contact.
fn intersects(a: Vec2, b: Vec2, c: Vec2, d: Vec2) -> bool {
    let (ac, ad, ca, cb) = (
        cross(a, b, c),
        cross(a, b, d),
        cross(c, d, a),
        cross(c, d, b),
    );
    (((ac < 0.0 && ad > 0.0) || (ac > 0.0 && ad < 0.0))
        && ((ca < 0.0 && cb > 0.0) || (ca > 0.0 && cb < 0.0)))
        || on(a, c, d)
        || on(b, c, d)
        || on(c, a, b)
        || on(d, a, b)
}
/// Even/odd containment with boundary included.
fn contains(r: &[Vec2], p: Vec2) -> bool {
    let n = size(r);
    let mut inside = false;
    for i in 0..n {
        let (a, b) = (r[i], r[(i + 1) % n]);
        if on(p, a, b) {
            return true;
        }
        if (a.y > p.y) != (b.y > p.y) && (cross(a, b, p) > 0.0) == (b.y > a.y) {
            inside = !inside;
        }
    }
    inside
}
/// Detect contact between ring boundaries.
fn rings_intersect(a: &[Vec2], b: &[Vec2]) -> bool {
    let (na, nb) = (size(a), size(b));
    for i in 0..na {
        for j in 0..nb {
            if intersects(a[i], a[(i + 1) % na], b[j], b[(j + 1) % nb]) {
                return true;
            }
        }
    }
    false
}
/// Validate a finite nondegenerate simple ring, preserving winding.
fn valid_ring(r: &[Vec2]) -> bool {
    let n = size(r);
    if n < 3 {
        return false;
    }
    let mut noncollinear = false;
    for i in 0..n {
        let (a, b, previous) = (r[i], r[(i + 1) % n], r[(i + n - 1) % n]);
        if !a.x.is_finite() || !a.y.is_finite() || a == b {
            return false;
        }
        let turn = cross(previous, a, b);
        if !turn.is_finite() || (turn == 0.0 && !on(a, previous, b)) {
            return false;
        }
        // Simplicity plus a non-collinear turn avoids a cancelling area sum.
        noncollinear |= turn != 0.0;
        for j in i + 1..n {
            if j != i + 1 && !(i == 0 && j == n - 1) && intersects(a, b, r[j], r[(j + 1) % n]) {
                return false;
            }
        }
    }
    noncollinear
}
/// Validate a simple exterior and disjoint strictly interior holes.
pub fn valid_polygon_area(exterior: &[Vec2], holes: &[Vec<Vec2>]) -> bool {
    if !valid_ring(exterior) {
        return false;
    }
    for (i, hole) in holes.iter().enumerate() {
        if !valid_ring(hole) || !contains(exterior, hole[0]) || rings_intersect(exterior, hole) {
            return false;
        }
        for other in &holes[..i] {
            if rings_intersect(hole, other) || contains(hole, other[0]) || contains(other, hole[0])
            {
                return false;
            }
        }
    }
    true
}
/// Intersect prevalidated areas in one plane, including all ring boundaries.
pub fn polygon_areas_intersect(
    a: &[Vec2],
    a_holes: &[Vec<Vec2>],
    b: &[Vec2],
    b_holes: &[Vec<Vec2>],
) -> bool {
    if a.is_empty() || b.is_empty() {
        return false;
    }
    for left in std::iter::once(a).chain(a_holes.iter().map(Vec::as_slice)) {
        for right in std::iter::once(b).chain(b_holes.iter().map(Vec::as_slice)) {
            if rings_intersect(left, right) {
                return true;
            }
        }
    }
    (contains(b, a[0]) && !b_holes.iter().any(|hole| contains(hole, a[0])))
        || (contains(a, b[0]) && !a_holes.iter().any(|hole| contains(hole, b[0])))
}
/// Classify a rectangle against prevalidated unwrapped rings; all boundary contact counts.
pub fn classify_polygon_rectangle(
    exterior: &[Vec2],
    holes: &[Vec<Vec2>],
    minimum: Vec2,
    maximum: Vec2,
) -> PolygonAreaRelation {
    if exterior.len() < 3
        || ![minimum.x, minimum.y, maximum.x, maximum.y]
            .iter()
            .all(|v| v.is_finite())
        || minimum.x > maximum.x
        || minimum.y > maximum.y
    {
        return PolygonAreaRelation::Outside;
    }
    let rectangle = [
        minimum,
        Vec2::new(maximum.x, minimum.y),
        maximum,
        Vec2::new(minimum.x, maximum.y),
    ];
    for ring in std::iter::once(exterior).chain(holes.iter().map(Vec::as_slice)) {
        if ring
            .iter()
            .any(|p| p.x >= minimum.x && p.x <= maximum.x && p.y >= minimum.y && p.y <= maximum.y)
            || rings_intersect(ring, &rectangle)
        {
            return PolygonAreaRelation::Boundary;
        }
    }
    let centre = Vec2::new((minimum.x + maximum.x) * 0.5, (minimum.y + maximum.y) * 0.5);
    if !contains(exterior, centre) || holes.iter().any(|hole| contains(hole, centre)) {
        return PolygonAreaRelation::Outside;
    }
    PolygonAreaRelation::Inside
}
