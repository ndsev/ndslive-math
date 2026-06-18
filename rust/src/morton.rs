// SPDX-License-Identifier: MIT
//! Morton (Z-order) encoding for 2D NDS coordinates.
//!
//! Faithful port of `python/src/ndslive/math/morton.py` and cross-checked
//! against `cpp/include/ndsmath/mortoncode.h`.

/// A 64-bit Morton (Z-order) code.
///
/// Wraps a raw `u64`. The encoder masks off bit 63 to preserve the NDS
/// semantics of the reference implementation.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct MortonCode(pub u64);

impl MortonCode {
    /// Construct a `MortonCode` from a raw 64-bit value.
    ///
    /// Most callers use [`MortonCode::from_nds_coordinates`] instead.
    pub fn new(morton_code: u64) -> Self {
        // Python masks to 64 bits; in Rust a u64 is already 64-bit.
        MortonCode(morton_code)
    }

    /// Encode NDS integer coordinates into a Morton (Z-order) code.
    ///
    /// `x` is NDS longitude (signed 32-bit), `y` is NDS latitude
    /// (signed 31-bit). Out-of-range inputs are wrapped, exactly as in the
    /// Python reference. Bit 63 is masked off.
    pub fn from_nds_coordinates(x: i32, y: i32) -> MortonCode {
        let x_base: i64 = 1 << 31;
        let y_base: i64 = 1 << 30;

        let mut x: i64 = x as i64;
        let mut y: i64 = y as i64;

        // Wrap x into [-2^31, 2^31) and y into [-2^30, 2^30).
        while x >= x_base {
            x -= 1 << 32;
        }
        while x < -x_base {
            x += 1 << 32;
        }
        while y >= y_base {
            y -= 1 << 31;
        }
        while y < -y_base {
            y += 1 << 31;
        }

        // Reinterpret the (now reduced) signed values as their two's-complement
        // bit patterns so that the AND/shift logic matches Python's behavior on
        // negative ints. Everything is then done with wrapping shifts in u64.
        let mut x: u64 = x as u64;
        let mut y: u64 = y as u64;

        let mut bit: u64 = 1;
        let mut morton_code: u64 = 0;

        y = y.wrapping_shl(1);

        for _ in 0..31 {
            morton_code |= x & bit;
            x = x.wrapping_shl(1);
            bit = bit.wrapping_shl(1);

            morton_code |= y & bit;
            y = y.wrapping_shl(1);
            bit = bit.wrapping_shl(1);
        }

        morton_code |= x & bit;
        // The final `x <<= 1` / `bit <<= 1` in the reference are dead stores
        // (their results are never read), so we omit them.

        morton_code &= !(1u64 << 63);

        MortonCode(morton_code)
    }

    /// Decode this Morton code back into NDS integer coordinates.
    ///
    /// Inverse of [`MortonCode::from_nds_coordinates`]. Returns `(x, y)` as
    /// signed integers: NDS longitude (32-bit) and NDS latitude (31-bit).
    pub fn to_nds_coordinates(&self) -> (i32, i32) {
        const YBASE: i64 = 1 << 30;
        const XBASE: i64 = 1 << 31;

        let mut bit: u64 = 1;
        let mut morton_code: u64 = self.0;
        let mut x: u64 = 0;
        let mut y: u64 = 0;

        for _ in 0..31 {
            x |= morton_code & bit;
            morton_code >>= 1;
            y |= morton_code & bit;
            bit <<= 1;
        }

        x |= morton_code & bit;
        // Reference does a final `morton_code >>= 1` here whose result is unused.

        let mut x = x as i64;
        let mut y = y as i64;

        if y >= YBASE {
            y -= 1 << 31;
        }
        if x >= XBASE {
            x -= 1 << 32;
        }

        (x as i32, y as i32)
    }

    /// Get the raw Morton code value (matches the C++/Python `value()` API).
    pub fn value(&self) -> u64 {
        self.0
    }
}

impl std::fmt::Display for MortonCode {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "MortonCode(value={})", self.0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn round_trip(x: i32, y: i32, expected: u64) {
        let m = MortonCode::from_nds_coordinates(x, y);
        assert_eq!(m.value(), expected, "encode ({x},{y})");
        let (dx, dy) = m.to_nds_coordinates();
        assert_eq!((dx, dy), (x, y), "decode ({x},{y})");
    }

    #[test]
    fn small_values() {
        round_trip(0, 0, 0);
        round_trip(1, 0, 1);
        round_trip(0, 1, 2);
        round_trip(1, 1, 3);
        round_trip(12345, 6789, 126387555);
    }

    #[test]
    fn negative_values() {
        round_trip(-12345, -6789, 9223372036728388255);
        round_trip(-(1 << 31), -(1 << 30), 6917529027641081856);
    }

    #[test]
    fn extremes() {
        round_trip((1 << 31) - 1, (1 << 30) - 1, 2305843009213693951);
        round_trip(1000000000, -1000000000, 2694675840375717888);
    }

    #[test]
    fn bit63_masked() {
        // No encoded value may ever have bit 63 set.
        for &(x, y) in &[
            (0, 0),
            (-1, -1),
            ((1 << 31) - 1, (1 << 30) - 1),
            (-(1 << 31), -(1 << 30)),
        ] {
            let m = MortonCode::from_nds_coordinates(x, y);
            assert_eq!(m.value() & (1u64 << 63), 0);
        }
    }
}
