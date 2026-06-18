# ndslive-math (Rust)

Coordinate math, packed tile IDs, and Morton (Z-order) codes for
[NDS.Live](https://nds.live/) geographic tiling.

This crate is a faithful Rust port of the Python reference implementation in
this repository (`python/src/ndslive/math`). All implementations (C++, Python,
Rust) are validated against the language-neutral golden vectors in
`test-vectors/parity_vectors.json`.

## Installation

```sh
cargo add ndslive-math
```

## Usage

```rust
use ndslive_math::{Wgs84, MortonCode, PackedTileId, NdsBoundingBox};

// WGS84 -> NDS integer coordinates (uses floor, per the NDS recommendation).
let point = Wgs84::new(11.585, 48.137); // Munich
let (nds_x, nds_y) = point.to_nds_coordinates();

// Round-trip back to degrees.
let back = Wgs84::from_nds_coordinates(nds_x, nds_y);

// Find the level-13 tile that contains the point.
let morton = MortonCode::from_nds_coordinates(nds_x, nds_y);
let tile = PackedTileId::from_morton_and_level(morton, 13).unwrap();

// Tile geometry and neighbour traversal.
let sw = tile.south_west_corner();
let ne = tile.north_east_corner(); // exclusive NE corner
let east = tile.east_neighbour();

// Bounding boxes in NDS space.
let bbox = NdsBoundingBox::from_wgs84_corners(
    &Wgs84::new(11.5, 48.1),
    &Wgs84::new(11.7, 48.2),
);

// Level 15 tile IDs are negative per the NDS.Live standard.
let l15 = PackedTileId::from_tile_index(0, 15).unwrap();
assert_eq!(l15.value(), -2147483648);
```

## API overview

- [`Wgs84`] — WGS84 lon/lat/alt point with NDS conversion (`to_nds_coordinates`
  uses **floor**), `distance_to`, `bearing_from`, `to_degree_minutes_seconds`,
  `degrees_to_meters` / `nds_distance_to_meters`.
- [`MortonCode`] — 64-bit Z-order encode/decode of signed NDS coordinates.
- [`PackedTileId`] — NDS.Live Packed Tile ID. The `value()` is a **signed**
  `i32` (negative for level 15); internally stored as `u32`. Constructors
  validate inputs and return `Result<_, TileIdError>`.
- [`NdsBoundingBox`] — integer rectangle in NDS space with `intersects` /
  `contains`, `from_tile`, `from_wgs84_corners`.
- [`get_tile_ids_for_bounding_box`] / [`bounding_box_from_tile_ids`] — bulk tile
  enumeration. `bounding_box_from_tile_ids` returns `(min_x, min_y, max_x - 1,
  max_y - 1)` (inclusive max), because tile NE corners are exclusive.

## Testing

```sh
cargo test
```

The integration test suite (`tests/parity.rs`) loads
`../test-vectors/parity_vectors.json` and asserts every section against this
port: integer results must match exactly; float results must match within the
`float_tolerance` (1e-6) declared in the vectors.

Coverage can be measured with [`cargo-llvm-cov`](https://github.com/taiki-e/cargo-llvm-cov):

```sh
cargo install cargo-llvm-cov
cargo llvm-cov --all-features
```

## License

MIT — see [LICENSE](LICENSE).
