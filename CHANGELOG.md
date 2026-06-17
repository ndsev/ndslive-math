# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [v0.6.0] - Unreleased

### Changed
- Prepare ndslive-math as the shared C++/Python tile-ID dependency for mapget and the MapViewer stack.

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
