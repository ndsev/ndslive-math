// SPDX-License-Identifier: BSD-3-Clause
//! A plain 2D vector that is *not* WGS84-normalized.
//!
//! The geometry layer ([`crate::Wgs84Aabb`] in particular) needs a raw
//! `(dx, dy)` extent that can legitimately exceed `360` / `180` degrees or be
//! negative — unlike [`crate::Wgs84`], whose constructor wraps longitude and
//! clamps latitude. Reusing `Wgs84` for a size/extent would silently corrupt
//! those values via normalization, so this small struct is used instead.
//!
//! Faithful port of `python/src/ndslive/math/vec2.py`.

use std::ops::{Add, Mul, Sub};

/// A raw, un-normalized 2D vector `(x, y)`.
///
/// `x` is the longitude/horizontal component, `y` the latitude/vertical
/// component. Supports component-wise `+` / `-` (with another [`Vec2`]) and
/// scalar multiplication.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Vec2 {
    /// Horizontal (longitude) component.
    pub x: f64,
    /// Vertical (latitude) component.
    pub y: f64,
}

impl Vec2 {
    /// Construct a [`Vec2`] from its two components.
    pub fn new(x: f64, y: f64) -> Self {
        Vec2 { x, y }
    }

    /// Return the component-wise absolute value.
    pub fn abs(self) -> Vec2 {
        Vec2 {
            x: self.x.abs(),
            y: self.y.abs(),
        }
    }
}

impl Default for Vec2 {
    fn default() -> Self {
        Vec2 { x: 0.0, y: 0.0 }
    }
}

impl Add for Vec2 {
    type Output = Vec2;
    fn add(self, other: Vec2) -> Vec2 {
        Vec2 {
            x: self.x + other.x,
            y: self.y + other.y,
        }
    }
}

impl Sub for Vec2 {
    type Output = Vec2;
    fn sub(self, other: Vec2) -> Vec2 {
        Vec2 {
            x: self.x - other.x,
            y: self.y - other.y,
        }
    }
}

impl Mul<f64> for Vec2 {
    type Output = Vec2;
    /// Component-wise scalar multiplication.
    fn mul(self, scalar: f64) -> Vec2 {
        Vec2 {
            x: self.x * scalar,
            y: self.y * scalar,
        }
    }
}

impl std::fmt::Display for Vec2 {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "Vec2(x={}, y={})", self.x, self.y)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn arithmetic_and_abs() {
        let a = Vec2::new(3.0, -4.0);
        let b = Vec2::new(1.0, 2.0);
        assert_eq!(a + b, Vec2::new(4.0, -2.0));
        assert_eq!(a - b, Vec2::new(2.0, -6.0));
        assert_eq!(a * 2.0, Vec2::new(6.0, -8.0));
        assert_eq!(a.abs(), Vec2::new(3.0, 4.0));
        assert_eq!(Vec2::default(), Vec2::new(0.0, 0.0));
        assert!(format!("{}", a).contains("Vec2(x="));
    }
}
