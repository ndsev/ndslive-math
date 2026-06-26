# ndslive-math

[![CI](https://github.com/ndsev/ndslive-math/actions/workflows/ci.yml/badge.svg)](https://github.com/ndsev/ndslive-math/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/ndsev/ndslive-math/branch/main/graph/badge.svg)](https://codecov.io/gh/ndsev/ndslive-math)
[![License: BSD-3-Clause](https://img.shields.io/badge/license-BSD--3--Clause-blue.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/ndslive-math.svg)](https://pypi.org/project/ndslive-math/)
[![npm](https://img.shields.io/npm/v/@ndsev/ndslive-math.svg)](https://www.npmjs.com/package/@ndsev/ndslive-math)
[![crates.io](https://img.shields.io/crates/v/ndslive-math.svg)](https://crates.io/crates/ndslive-math)

Mathematical utilities for [NDS.Live](https://nds.live/), provided as a single,
behaviour-identical library across **six languages**: C++, Python, Java,
JavaScript/TypeScript, Go, and Rust.

## What it does

`ndslive-math` implements the small set of geometry primitives that NDS.Live
tooling relies on:

- **WGS84 ↔ NDS coordinates** — convert between geographic longitude/latitude
  (degrees) and the NDS integer coordinate space, plus distance/bearing helpers.
- **Packed Tile IDs** — encode/decode NDS.Live tile identifiers (a Morton index
  plus a level), with geometry accessors and neighbour traversal.
- **Morton codes** — Z-order curve encoding/decoding for spatial indexing.
- **Bounding boxes** — axis-aligned boxes in NDS space, and helpers to enumerate
  the tiles covering a box.

### A 60-second primer on the concepts

NDS.Live partitions the globe with a quad-tree-like tiling scheme. A point's
geographic position (WGS84 longitude/latitude in degrees) maps to a pair of
fixed-point **NDS integer coordinates** (X is 32-bit, Y is 31-bit). Interleaving
the bits of those two integers gives a **Morton code** (a Z-order curve value),
which makes nearby points have nearby codes. A **Packed Tile ID** combines a
truncated Morton index with a **level** (0–15) to name one square tile of the
world; higher levels mean smaller tiles. This library is just the exact, shared
arithmetic for moving between these representations.

## Installation

| Language | Install |
|---|---|
| **Python** | `pip install ndslive-math` → `from ndslive.math import Wgs84, PackedTileId, MortonCode` |
| **JavaScript/TS** | `npm install @ndsev/ndslive-math` |
| **Rust** | `cargo add ndslive-math` |
| **Go** | `go get github.com/ndsev/ndslive-math/go` |
| **Java** | Gradle/Maven artifact `de.klebert-engineering:ndslive-math` (see [`java/README.md`](java/README.md)) |
| **C++** | Header/CMake library — see below |

For per-language usage and examples, see the README in each directory:
[`python/`](python/README.md) · [`cpp/`](cpp/README.md) · [`java/`](java/README.md)
· [`js/`](js/README.md) · [`go/`](go/README.md) · [`rust/`](rust/README.md).

### C++ via CMake FetchContent

The C++ code lives in `cpp/`; a sparse checkout keeps the rest of the repo out
of your build:

```cmake
if (NOT TARGET ndsmath)
  FetchContent_Declare(ndsmath
    GIT_REPOSITORY "https://github.com/ndsev/ndslive-math.git"
    GIT_TAG        "v0.5.2"
    GIT_SHALLOW    ON)
  FetchContent_GetProperties(ndsmath)
  if(NOT ndsmath_POPULATED)
    FetchContent_Populate(ndsmath)
    execute_process(COMMAND git sparse-checkout init --cone WORKING_DIRECTORY ${ndsmath_SOURCE_DIR})
    execute_process(COMMAND git sparse-checkout set cpp     WORKING_DIRECTORY ${ndsmath_SOURCE_DIR})
    execute_process(COMMAND git checkout                    WORKING_DIRECTORY ${ndsmath_SOURCE_DIR})
  endif()
  add_subdirectory(${ndsmath_SOURCE_DIR}/cpp ${CMAKE_BINARY_DIR}/_deps/ndsmath-build)
endif()
```

> **Note:** the C++ target, include path (`<ndsmath/...>`), and `ndsmath`
> namespace are unchanged for backward compatibility — only the repository name
> is `ndslive-math`. The C++ library also depends on
> [glm](https://github.com/g-truc/glm); add it to your project as well.

A **vcpkg** port is provided in [`cpp/vcpkg-port/`](cpp/vcpkg-port) (usable as an
overlay port now; upstream-registry submission follows the first public release).
The library also supports `install` + `find_package(ndsmath CONFIG)`. See
[`cpp/README.md`](cpp/README.md) for all consumption options.

## Quick example (Python)

```python
from ndslive.math import Wgs84, PackedTileId, MortonCode

point = Wgs84(lon=13.404954, lat=52.520008)   # Berlin
nds_x, nds_y = point.to_nds_coordinates()

morton = MortonCode.from_nds_coordinates(nds_x, nds_y)
tile = PackedTileId.from_morton_and_level(morton, level=13)
print(tile.value, tile.south_west_corner(), tile.east_neighbour().value)
```

## Cross-language parity

All six implementations are validated against a single set of golden vectors,
[`test-vectors/parity_vectors.json`](test-vectors/parity_vectors.json), generated
from the Python reference implementation. Integer results must match exactly and
floating-point results within a fixed tolerance, so every language stays
bit-for-bit consistent. CI runs each language's suite against these vectors on
every change. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for how to regenerate them.

## Releases

Unified `vX.Y.Z` git tags drive releases across all languages. Update
[`CHANGELOG.md`](CHANGELOG.md) ([Keep a Changelog](https://keepachangelog.com/)
format, per-language subsections) in every change; CI enforces this. Pre-release
builds publish from `main`; tagged releases publish to the public registries.

## Contributing

Issue reports and feature requests are welcome — see
[`CONTRIBUTING.md`](CONTRIBUTING.md). We do not currently accept external pull
requests; changes are implemented by the NDS team. For security reports, see
[`SECURITY.md`](SECURITY.md).

## License

BSD-3-Clause. See [`LICENSE`](LICENSE).
