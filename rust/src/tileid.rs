// SPDX-License-Identifier: MIT
//! NDS.Live Packed Tile IDs and bounding-box tile enumeration.
//!
//! Faithful port of `python/src/ndslive/math/tileid.py`, cross-checked against
//! `cpp/include/ndsmath/packedtileid.h`.

use crate::morton::MortonCode;
use crate::wgs84::Wgs84;

/// Error returned when constructing or validating a [`PackedTileId`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TileIdError {
    /// The level is outside the valid range 0..=15.
    InvalidLevel(u32),
    /// The morton number is outside the valid range for the given level.
    InvalidMortonNumber {
        /// The offending morton number.
        morton: i64,
        /// The level it was supplied for.
        level: u32,
        /// The maximum allowed morton number for `level`.
        max: u64,
    },
    /// The packed value is below the minimum valid packed tile id (`1 << 16`).
    ValueTooSmall(i32),
}

impl std::fmt::Display for TileIdError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            TileIdError::InvalidLevel(level) => {
                write!(f, "Invalid level {level} (must be 0-15)")
            }
            TileIdError::InvalidMortonNumber { morton, level, max } => write!(
                f,
                "Invalid morton number {morton} for level {level} (allowed: 0-{max})"
            ),
            TileIdError::ValueTooSmall(value) => write!(
                f,
                "Invalid PackedTileId({value}): value must be >= {} or negative for level 15",
                1u32 << 16
            ),
        }
    }
}

impl std::error::Error for TileIdError {}

/// An NDS.Live Packed Tile ID.
///
/// Per the NDS.Live standard, tile IDs are signed 32-bit integers: levels 0-14
/// are positive, while level 15 values are negative (bit 31 is the sign bit).
/// Internally the value is stored as a `u32` so that bit operations need not
/// deal with the sign bit; conversion to/from signed happens only at the API
/// boundary (see [`PackedTileId::value`] and [`PackedTileId::new`]).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct PackedTileId {
    /// Internal unsigned representation.
    value: u32,
}

impl PackedTileId {
    /// Construct a `PackedTileId` from a signed `i32` tile ID value.
    ///
    /// Accepts the signed representation (negative for level 15). For a
    /// constructor that also accepts the unsigned representation or
    /// out-of-range values, see [`PackedTileId::from_i64`].
    pub fn new(value: i32) -> Result<Self, TileIdError> {
        Self::from_i64(value as i64)
    }

    /// Construct a `PackedTileId` from an `i64`, accepting both signed and
    /// unsigned 32-bit representations (matching the Python constructor).
    ///
    /// Negative values are interpreted as signed `i32` and converted to the
    /// unsigned internal representation; values `>= 2^32` are masked to 32 bits.
    pub fn from_i64(value: i64) -> Result<Self, TileIdError> {
        let stored: u32 = if value < 0 {
            // Convert signed int32 to unsigned (e.g. -2147483648 -> 2147483648).
            (value + (1i64 << 32)) as u32
        } else if value >= (1i64 << 32) {
            (value as u64 & 0xFFFF_FFFF) as u32
        } else {
            value as u32
        };

        let tile = PackedTileId { value: stored };
        tile.validate()?;
        Ok(tile)
    }

    /// Get the tile ID value as a signed `i32`, per the NDS.Live standard.
    ///
    /// Level 15 tiles return negative values; levels 0-14 return positive
    /// values.
    pub fn value(&self) -> i32 {
        // A `u32 as i32` cast reinterprets the bits as two's complement: values
        // with bit 31 set (level 15) become negative, exactly as the Python
        // `value` property computes via `_value - (1 << 32)`.
        self.value as i32
    }

    /// Create a `PackedTileId` directly from a tile morton number and level,
    /// without any coordinate conversion.
    ///
    /// `morton_number` must be in `0..=2^(2*level+1) - 1`.
    pub fn from_tile_index(morton_number: u32, level: u32) -> Result<Self, TileIdError> {
        if level > 15 {
            return Err(TileIdError::InvalidLevel(level));
        }

        let max_morton: u64 = (1u64 << (2 * level + 1)) - 1;
        if (morton_number as u64) > max_morton {
            return Err(TileIdError::InvalidMortonNumber {
                morton: morton_number as i64,
                level,
                max: max_morton,
            });
        }

        let value: u32 = morton_number + (1u32 << (16 + level));
        PackedTileId::from_i64(value as i64)
    }

    /// Create a `PackedTileId` for the tile at `level` that contains the
    /// full-precision NDS coordinates encoded in `morton_code`.
    ///
    /// Note: the resulting tile's [`PackedTileId::morton_number`] generally
    /// differs from `morton_code.value()`.
    pub fn from_morton_and_level(morton_code: MortonCode, level: u32) -> Result<Self, TileIdError> {
        if level > 15 {
            return Err(TileIdError::InvalidLevel(level));
        }

        let (x_coord, y_coord) = morton_code.to_nds_coordinates();

        // Move into the unsigned domain (matches Python's add of 2^32 / 2^31).
        let x_coord: u64 = if x_coord < 0 {
            (x_coord as i64 + (1i64 << 32)) as u64
        } else {
            x_coord as u64
        };
        let y_coord: u64 = if y_coord < 0 {
            (y_coord as i64 + (1i64 << 31)) as u64
        } else {
            y_coord as u64
        };

        let n_level = 31 - level;
        let n_x = (x_coord >> n_level) as i32;
        let n_y = (y_coord >> n_level) as i32;

        let temp = MortonCode::from_nds_coordinates(n_x, n_y);

        let value: u64 = temp.value() + (1u64 << (16 + level));
        PackedTileId::from_i64(value as i64)
    }

    /// Level of the tile (0..=15).
    pub fn level(&self) -> u32 {
        let mut level = 0u32;
        let mut tile_id = self.value >> 16;
        while tile_id > 1 {
            tile_id >>= 1;
            level += 1;
        }
        level
    }

    /// Size of the tile in NDS coordinate units (`1 << (31 - level)`).
    pub fn size(&self) -> i64 {
        1i64 << (31 - self.level())
    }

    /// Tile dimensions in meters at the tile's center latitude.
    ///
    /// Returns `(width_meters, height_meters)`.
    pub fn dimensions_in_meters(&self) -> (f64, f64) {
        let (center_x, center_y) = self.center();
        let center_wgs = Wgs84::from_nds_coordinates(center_x as i32, center_y as i32);
        let tile_size = self.size() as i32;
        Wgs84::nds_distance_to_meters(tile_size, tile_size, center_wgs.lat)
    }

    /// Center of the tile in NDS coordinates `(x, y)`.
    pub fn center(&self) -> (i64, i64) {
        let (x, y) = self.south_west_corner();
        let half_size = self.size() / 2;
        (x + half_size, y + half_size)
    }

    /// South-west corner of the tile in NDS coordinates `(x, y)`.
    pub fn south_west_corner(&self) -> (i64, i64) {
        let morton_number = self.morton_number() as u64;
        let level = self.level();
        let shift = 63 - (2 * level + 1);
        let (x, y) = MortonCode::new(morton_number << shift).to_nds_coordinates();
        (x as i64, y as i64)
    }

    /// North-east corner of the tile in NDS coordinates `(x, y)`.
    ///
    /// This boundary is **exclusive** — it is the first point outside the tile.
    pub fn north_east_corner(&self) -> (i64, i64) {
        let (x, y) = self.south_west_corner();
        let size = self.size();
        (x + size, y + size)
    }

    /// Morton number of the tile (the packed value minus the level offset).
    pub fn morton_number(&self) -> u32 {
        let tile_level = self.level();
        self.value - (1u32 << (16 + tile_level))
    }

    /// Validate this tile id against the NDS constraints.
    fn validate(&self) -> Result<(), TileIdError> {
        let min_packed_tile_id: u32 = 1 << 16;
        if self.value < min_packed_tile_id {
            return Err(TileIdError::ValueTooSmall(self.value()));
        }

        let tile_level = self.level();
        let morton = self.morton_number();
        let max_morton: u64 = (1u64 << (2 * tile_level + 1)) - 1;

        // morton_number is computed as an unsigned subtraction that cannot
        // underflow for a value >= min_packed_tile_id, so only the upper bound
        // can be violated.
        if (morton as u64) > max_morton {
            return Err(TileIdError::InvalidMortonNumber {
                morton: morton as i64,
                level: tile_level,
                max: max_morton,
            });
        }

        Ok(())
    }

    /// Extract X and Y coordinates from a tile morton number.
    ///
    /// X has `level + 1` bits, Y has `level` bits.
    fn deinterleave_morton(morton: u32, level: u32) -> (u32, u32) {
        let mut x = 0u32;
        let mut y = 0u32;
        for i in 0..level {
            if morton & (1u32 << (2 * i)) != 0 {
                x |= 1u32 << i;
            }
            if morton & (1u32 << (2 * i + 1)) != 0 {
                y |= 1u32 << i;
            }
        }
        if morton & (1u32 << (2 * level)) != 0 {
            x |= 1u32 << level;
        }
        (x, y)
    }

    /// Create a tile morton number from X and Y coordinates.
    ///
    /// X has `level + 1` bits, Y has `level` bits.
    fn interleave_coords(x: u32, y: u32, level: u32) -> u32 {
        let mut morton = 0u32;
        for i in 0..level {
            if x & (1u32 << i) != 0 {
                morton |= 1u32 << (2 * i);
            }
            if y & (1u32 << i) != 0 {
                morton |= 1u32 << (2 * i + 1);
            }
        }
        if x & (1u32 << level) != 0 {
            morton |= 1u32 << (2 * level);
        }
        morton
    }

    /// Tile to the west at the same level (wraps at the antimeridian).
    pub fn west_neighbour(&self) -> PackedTileId {
        let level = self.level();
        let morton = self.morton_number();
        let (mut x, y) = Self::deinterleave_morton(morton, level);
        let max_x = (1u32 << (level + 1)) - 1;
        x = x.wrapping_sub(1) & max_x;
        let new_morton = Self::interleave_coords(x, y, level);
        PackedTileId::from_tile_index(new_morton, level).expect("valid neighbour")
    }

    /// Tile to the east at the same level (wraps at the antimeridian).
    pub fn east_neighbour(&self) -> PackedTileId {
        let level = self.level();
        let morton = self.morton_number();
        let (mut x, y) = Self::deinterleave_morton(morton, level);
        let max_x = (1u32 << (level + 1)) - 1;
        x = x.wrapping_add(1) & max_x;
        let new_morton = Self::interleave_coords(x, y, level);
        PackedTileId::from_tile_index(new_morton, level).expect("valid neighbour")
    }

    /// Tile to the south at the same level (wraps at the south pole).
    pub fn south_neighbour(&self) -> PackedTileId {
        let level = self.level();
        let morton = self.morton_number();
        let (x, mut y) = Self::deinterleave_morton(morton, level);
        let max_y = (1u32 << level) - 1;
        y = y.wrapping_sub(1) & max_y;
        let new_morton = Self::interleave_coords(x, y, level);
        PackedTileId::from_tile_index(new_morton, level).expect("valid neighbour")
    }

    /// Tile to the north at the same level (wraps at the north pole).
    pub fn north_neighbour(&self) -> PackedTileId {
        let level = self.level();
        let morton = self.morton_number();
        let (x, mut y) = Self::deinterleave_morton(morton, level);
        let max_y = (1u32 << level) - 1;
        y = y.wrapping_add(1) & max_y;
        let new_morton = Self::interleave_coords(x, y, level);
        PackedTileId::from_tile_index(new_morton, level).expect("valid neighbour")
    }
}

impl std::fmt::Display for PackedTileId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "PackedTileId(value={})", self.value())
    }
}

/// Floor division for `i64` (matches Python's `//`).
///
/// Rust's `/` truncates toward zero, so `div_euclid` differs from Python `//`
/// for mixed-sign operands. For a positive divisor (always the case here, since
/// `tile_size > 0`), `div_euclid` equals floor division.
#[inline]
fn floor_div(a: i64, b: i64) -> i64 {
    a.div_euclid(b)
}

/// Get all tile IDs that intersect a bounding box given by NDS coordinates.
///
/// `(sw_x, sw_y)` is the south-west corner and `(ne_x, ne_y)` the north-east
/// corner, both inclusive. Faithful port of the Python
/// `get_tile_ids_for_bounding_box`.
pub fn get_tile_ids_for_bounding_box(
    sw_x: i64,
    sw_y: i64,
    ne_x: i64,
    ne_y: i64,
    level: u32,
) -> Vec<PackedTileId> {
    let mut tile_ids = Vec::new();

    let tile_size: i64 = 1 << (31 - level);

    // Floor division so negative coordinates map to the correct tile, matching
    // Python's `//` (Rust `/` would truncate toward zero).
    let start_tile_x = floor_div(sw_x, tile_size);
    let start_tile_y = floor_div(sw_y, tile_size);
    let end_tile_x = floor_div(ne_x, tile_size);
    let end_tile_y = floor_div(ne_y, tile_size);

    let mut tile_y = start_tile_y;
    while tile_y <= end_tile_y {
        let mut tile_x = start_tile_x;
        while tile_x <= end_tile_x {
            let tile_sw_x = tile_x * tile_size;
            let tile_sw_y = tile_y * tile_size;

            // from_nds_coordinates / morton encoding operate on i32 with
            // wrapping, matching the Python reference's wrapping reduction.
            let morton = MortonCode::from_nds_coordinates(tile_sw_x as i32, tile_sw_y as i32);
            let tile_id = PackedTileId::from_morton_and_level(morton, level)
                .expect("tile within bounding box must be valid");
            tile_ids.push(tile_id);

            tile_x += 1;
        }
        tile_y += 1;
    }

    tile_ids
}

/// Create a tight bounding box (in NDS coordinates) covering all the tiles.
///
/// Returns `(min_x, min_y, max_x, max_y)` where `max_x`/`max_y` are the **last
/// inclusive** points inside the tiles — i.e. the exclusive NE corner minus 1,
/// matching the Python `bounding_box_from_tile_ids`.
///
/// Returns `None` if `tiles` is empty.
pub fn bounding_box_from_tile_ids(tiles: &[PackedTileId]) -> Option<(i64, i64, i64, i64)> {
    let (first, rest) = tiles.split_first()?;

    let (mut min_x, mut min_y) = first.south_west_corner();
    let (mut max_x, mut max_y) = first.north_east_corner();

    for tile in rest {
        let (sw_x, sw_y) = tile.south_west_corner();
        let (ne_x, ne_y) = tile.north_east_corner();
        min_x = min_x.min(sw_x);
        min_y = min_y.min(sw_y);
        max_x = max_x.max(ne_x);
        max_y = max_y.max(ne_y);
    }

    // NE corner is exclusive; subtract 1 to make it the last inclusive point.
    Some((min_x, min_y, max_x - 1, max_y - 1))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn level_15_is_negative() {
        let t = PackedTileId::from_tile_index(0, 15).unwrap();
        assert_eq!(t.value(), -2147483648);
        assert_eq!(t.level(), 15);
        assert_eq!(t.morton_number(), 0);
    }

    #[test]
    fn signed_unsigned_constructors_agree() {
        let a = PackedTileId::from_i64(-2147483648).unwrap();
        let b = PackedTileId::from_i64(2147483648).unwrap();
        assert_eq!(a, b);
        assert_eq!(a.value(), -2147483648);
    }

    #[test]
    fn max_level15_tile() {
        let t = PackedTileId::from_tile_index((1 << 31) - 1, 15).unwrap();
        assert_eq!(t.value(), -1);
    }

    #[test]
    fn level14_positive() {
        let t = PackedTileId::from_tile_index(0, 14).unwrap();
        assert_eq!(t.value(), 1073741824);
    }

    #[test]
    fn invalid_level() {
        assert!(matches!(
            PackedTileId::from_tile_index(0, 16),
            Err(TileIdError::InvalidLevel(16))
        ));
    }

    #[test]
    fn invalid_morton() {
        // level 0 allows morton 0..=1.
        assert!(PackedTileId::from_tile_index(2, 0).is_err());
    }

    #[test]
    fn corners_and_center() {
        let t = PackedTileId::from_tile_index(0, 0).unwrap();
        assert_eq!(t.size(), 2147483648);
        assert_eq!(t.south_west_corner(), (0, 0));
        assert_eq!(t.north_east_corner(), (2147483648, 2147483648));
        assert_eq!(t.center(), (1073741824, 1073741824));
    }

    #[test]
    fn bbox_floor_div_negative() {
        // sw at a negative coordinate must use floor division.
        let tiles = get_tile_ids_for_bounding_box(-1, -1, 0, 0, 1);
        assert!(!tiles.is_empty());
    }

    #[test]
    fn bbox_from_single_tile() {
        let t = PackedTileId::from_i64(131072).unwrap();
        let bbox = bounding_box_from_tile_ids(&[t]).unwrap();
        assert_eq!(bbox, (0, 0, 1073741823, 1073741823));
    }

    #[test]
    fn empty_bbox_returns_none() {
        assert!(bounding_box_from_tile_ids(&[]).is_none());
    }
}
