# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Project
- **BREAKING (licensing):** Relicensed from the proprietary NDS license to
  **BSD-3-Clause**. See `LICENSE`.
- Open-sourcing preparation: added `CONTRIBUTING.md` (issues-only policy),
  `SECURITY.md`, a root `LICENSE` with byte-identical per-language copies, and a
  language-neutral golden parity-vector suite under `test-vectors/`.
- CI now builds and tests **all** implementations — C++ (Linux/macOS/Windows),
  Python 3.10–3.14, Java, JavaScript/TypeScript, Go, Rust — validates
  cross-language parity, checks LICENSE consistency, and uploads coverage to
  Codecov. Replaced the NDS Artifactory deploy with public-registry publishing
  (PyPI Trusted Publishing/OIDC, npm, crates.io, Maven Central); all publish
  channels are wired but gated behind `ENABLE_*_PUBLISH` repo variables until the
  accounts/OIDC trust are provisioned.
- Added SPDX `BSD-3-Clause` headers across all source files.
- Static analysis & quality: **CodeQL** (Python, JS/TS, Go, Java, C++) and
  **Dependabot** (all ecosystems) workflows; **Codecov** gate at 95% project +
  patch coverage. Adopted formatters/linters across every language — Python
  (ruff), C++ (clang-format), Rust (rustfmt + clippy), Go (gofmt + vet),
  JavaScript/TS (ESLint + Prettier), Java (Spotless) — enforced by a CI `lint`
  job. Existing code reformatted to match; Go and Rust test coverage raised
  above the 95% gate.
- CI: exempt Dependabot PRs from the `check-changelog` job (dependency bumps
  don't carry user-facing changelog entries).

### Added
- **Java** implementation (`java/`, Gradle; Maven coordinates `io.github.ndsev:ndslive-math`).
- **JavaScript/TypeScript** implementation (`js/`, npm package `@ndsev/ndslive-math`).
- **Go** implementation (`go/`, module `github.com/ndsev/ndslive-math/go`).
- **Rust** implementation (`rust/`, crate `ndslive-math`).
- **C++:** CMake `install` + package-config (`find_package(ndsmath CONFIG)` →
  `ndsmath::ndsmath`), and a **vcpkg** port in `cpp/vcpkg-port/` (usable as an
  overlay port; upstream submission after the first public release). GLM is now
  consumed via `find_package` when available, falling back to FetchContent.

### Changed
- **Python:** added 3.14 to supported/tested versions; corrected the repository
  URLs and switched the license classifier to `BSD` in `pyproject.toml`.
- **C++:** **BREAKING:** `PackedTileId::value()` now returns signed `int32` per
  the NDS.Live standard (level-15 tiles are negative), instead of `uint32_t`.
  Migrated the C++ test suite off Catch2 to a dependency-free harness that
  validates against the shared parity vectors; added Windows to the C++ CI matrix.
- **C++:** **BREAKING (behavior):** fixed spec-compliance bugs verified against
  the normative tiling spec — north/south (and east/west) neighbour traversal
  rewritten via deinterleave/wrap/reinterleave (the old bit-walk produced
  out-of-range tile numbers); `lonNdsDelta`/`latNdsDelta` corrected to `360/2^32`
  and `180/2^31` (were ~2× too small); `from_morton_and_level` now wraps negative
  coordinates by `2^32`/`2^31` (was off by one). Added `boundingBoxFromTileIds`.
  The C++ parity test now validates the full golden set.

## [v0.5.2] - 2026-04-27

### Changed
- Curate the public surface for cleaner generated API reference (Sphinx + downstream renderers like the NDS.Live developer portal).

## [v0.5.1] - 2026-03-12

### Changed
- Use floor instead of truncate for WGS84 to NDS coordinate conversion (C++ and Python)

## [v0.5.0] - 2025-12-03

### Project
- Introduced unified versioning for C++ and Python (previously separate `cpp-v*` and `python-v*` tags)
- Python version jumps from 0.3.0 to 0.5.0 to align with C++ (0.4.0 was never published to Artifactory)

### Python

#### Added
- `from_tile_index()` class method for direct tile construction from morton number and level
- `is_valid()` method to PackedTileId for validating tile IDs
- Neighbor methods: `north_neighbour()`, `south_neighbour()`, `east_neighbour()`, `west_neighbour()` with proper boundary wrapping
- `dimensions_in_meters()` method to get tile dimensions in meters at center latitude
- `debug_info()` function for debugging tile information with neighbors
- `bounding_box_from_tile_ids()` function returning minimal AABB in NDS coords
- `NdsBoundingBox` dataclass with `from_wgs84_corners()`, `from_tile()`, `intersects()`, `contains()` methods
- `degrees_to_meters()` and `nds_distance_to_meters()` to Wgs84

#### Changed
- **BREAKING:** PackedTileId now uses signed int32 API per NDS.Live standard (level 15 tiles return negative values from `.value`)
- Improve docs for `from_morton_and_level()` clarifying it finds containing tile

#### Removed
- Remove obsolete `requirements.txt` and `setup.py` (migrated to pyproject.toml)

### C++

#### Added
- `fromTileIndex()` static method for direct tile construction from morton number and level
- `dimensionsInMeters()` method to PackedTileId for getting tile dimensions in meters
- `degreesToMeters()` and `ndsDistanceToMeters()` methods to Wgs84 for distance conversions
- `DeltaInMeters<T>` type alias for distance measurements
- `NdsBoundingBox` struct with `fromWgs84Corners()`, `fromTile()`, `intersects()`, `contains()` methods

#### Changed
- Uses unified versioning with `v*` tags (no longer separate `cpp-v*` tags)
- Improve API docs for `PackedTileId(MortonCode, level)` clarifying it finds containing tile

## [C++ v0.4.0] - 2025-09-09

### Fixed
- Avoid using GNU constants which are not available on MSVC

## [Python v0.3.0] - 2025-07-23

### Added
- `get_tile_ids_for_bounding_box()` function to get tile IDs from NDS bounding box

## [C++ v0.3.0] - 2025-07-23

### Added
- `getTileIdsForBoundingBox()` function to get tile IDs from NDS bounding box

## [C++ v0.2.0] - 2025-06-30

### Added
- Polygon triangulation support

## [Python v0.2.0] - 2025-05-29

### Changed
- Renamed package to `ndslive.math` for NDS.Live Python SDK integration
- Use namespace package scheme (PEP 420)
- Updated LICENSE to reference license agreements

## [Python v0.1.1] - 2025-04-29

### Fixed
- Rewrote `normalize()` method in `Wgs84` to correctly wrap longitude and latitude values
- Fixed NDS Coordinates <-> WGS84 coordinate conversion
- Improved `morton_number()` computation with level-specific offsets

### Added
- `value()` method to MortonCode matching C++ API
- Extensive tests for `Wgs84`, `MortonCode`, and `PackedTileId`

### Changed
- `MortonCode` now ensures a 64-bit unsigned integer
- Inputs in `from_nds_coordinates` are type-cast to integers, 63rd bit masked off

## [C++ v0.1.1] - 2025-04-23

### Fixed
- Ensure C++ version builds standalone (fix missing deps)
- Fix VERSION file misinterpreted as header when using CMake FetchContent

## [C++ v0.1.0] - 2025-03-25

### Added
- Initial C++ release with PackedTileId, MortonCode, Wgs84
