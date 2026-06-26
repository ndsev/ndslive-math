# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Project
- CodeQL: scoped analysis to our own code by ignoring the `build/` tree (which
  CMake/FetchContent fills with third-party GLM/Catch2 sources), removing the
  bulk of the open alerts, and cleared the remaining minor source findings.

### Fixed
- **Go:** removed dead-store assignments in `morton.go` (no behavior change).
- **C++:** dropped a redundant, always-true sign-adjust branch in
  `MortonCode::toNdsCoordinates` — an `int32_t` already carries the sign bit of
  the 32-bit `x` coordinate (`XBASE = 1<<31` had silently overflowed to
  `INT32_MIN`, making the guard always true). Decode output is unchanged
  (parity-verified).
- **Java:** renamed shadowing locals in `Wgs84.bearingFrom`.
- **Python:** `PackedTileId` uses `functools.total_ordering` for full, consistent
  comparison operators.

## [v1.0.0] - 2026-06-26

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
- Coverage: added C++ instrumentation (a `NDSMATH_COVERAGE` CMake option +
  `gcovr` on Ubuntu) and a JS `lcov` reporter, so **all six** languages now
  upload to Codecov (previously only Python, Java, Go, and Rust). Added C++ unit
  tests for the polygon / `Wgs84AABB` / triangulation layer (and
  `MortonCode::fromWgs84Coordinates`) to keep C++ above the coverage gate.
- Release readiness: completed the publishing pipeline so a single `vX.Y.Z` tag
  publishes every package. Maven Central now goes through the **Central Portal**
  with GPG signing (`com.vanniktech.maven.publish`); npm and crates.io versions
  are derived from the tag; the PyPI publish jobs no longer depend on the
  tag-skipped `check-changelog`; and the per-language manifests are aligned to
  `1.0.0`. The PyPI build pins the version from the tag
  (`SETUPTOOLS_SCM_PRETEND_VERSION`) and builds the `python/` project directly,
  for an exact version and a Python-only sdist; `setuptools-scm` is also told to
  match only `v[0-9]*` tags so the `go/*` module tags don't break it.

### Added
- **Geometry layer in all six languages.** Ported the previously C++-only
  `Polygon` (orientation), `Wgs84AABB` (axis-aligned bounding box: contains /
  intersects / corners / tile coverage / antimeridian split), `Wgs84Polygon`
  (separating-axis collision, bounding box, median) and ear-clipping
  `PolygonTriangulation` to Python, Java, JavaScript/TypeScript, Go, and Rust.
  The deterministic operations are bit-locked across languages by new
  `parity_vectors.json` sections; triangulation is unit-tested per language
  (its output ordering is not canonical).
- **Java** implementation (`java/`, Gradle; Maven coordinates `live.nds:ndslive-math`).
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
- **Python:** added type hints across the public API and a `py.typed` marker
  (PEP 561, shipped in the wheel) so downstream type checkers use them; added a
  mypy gate to the CI `lint` job.
- **JS/TS:** upgraded the dev toolchain to ESLint 10, Vitest 4, and TypeScript 6
  (consolidates the individual Dependabot JS bumps); removed a dead store in
  `morton.ts` flagged by ESLint 10's `no-useless-assignment` (no behavior change).
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

### Fixed
- **C++:** `Wgs84AABB::intersects()` could recurse until the stack overflowed for
  any box pair where neither box held a corner of the other (fully disjoint boxes
  *and* cross-shaped overlaps), and also returned the wrong answer for
  cross-shaped overlaps. Replaced the corner-containment logic with a standard
  axis-aligned interval-overlap test (O(1), non-recursive).
- **All languages:** `Wgs84Polygon.median()` returned its result with longitude
  and latitude swapped (the C++ reference built `Wgs84(meanLat, meanLon)` against
  a `(lon, lat)` constructor). It now returns a correct `(meanLon, meanLat)`
  centroid in every language, locked by the `wgs84_polygon` parity vectors.
- **C++:** `Wgs84AABB::numTileIds()` cast a negative-size (invalid) box's
  negative tile-count `double` to `uint32_t` — undefined behaviour that clang
  clamped to 0 but gcc/MSVC wrapped to a huge value, corrupting `tileLevel()`.
  It now returns 0 for a non-positive count (defined and consistent).

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
