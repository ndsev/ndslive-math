# ndsmath

C++ implementation of `ndslive-math` — math utilities for NDS.Live: WGS84
coordinates, Packed Tile IDs, Morton (Z-order) codes, and NDS bounding boxes.

Requires a C++20 compiler and CMake ≥ 3.14. Depends on
[GLM](https://github.com/g-truc/glm).

> The library target, include path (`<ndsmath/...>`), and `ndsmath` namespace are
> kept stable for existing consumers; only the repository is named `ndslive-math`.

## Consuming the library

### vcpkg

A port is maintained in [`vcpkg-port/`](vcpkg-port/). Until it lands in the
upstream registry it can be used as an overlay port:

```bash
vcpkg install ndsmath --overlay-ports=<path-to-repo>/cpp/vcpkg-port
```

```cmake
find_package(ndsmath CONFIG REQUIRED)
target_link_libraries(main PRIVATE ndsmath::ndsmath)
```

### Installed / find_package

```bash
cmake -S cpp -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
cmake --install build --prefix /your/prefix
```

Then, with GLM available to CMake (e.g. via vcpkg or your system):

```cmake
find_package(ndsmath CONFIG REQUIRED)
target_link_libraries(main PRIVATE ndsmath::ndsmath)
```

### CMake FetchContent (no package manager)

A sparse checkout keeps the rest of the monorepo out of your build:

```cmake
include(FetchContent)
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

target_link_libraries(main PRIVATE ndsmath::ndsmath)
```

When consumed this way, GLM is resolved via `find_package(glm)` if available, and
otherwise fetched automatically. Tests and install rules are off by default for
non-top-level builds.

## Usage

```cpp
#include <ndsmath/wgs84.h>
#include <ndsmath/packedtileid.h>

ndsmath::Wgs84<double> point(13.404954, 52.520008);   // Berlin (lon, lat)
int32_t x, y;
point.toNdsCoordinates(x, y);

auto tile = ndsmath::PackedTileId::fromTileIndex(0, 13);
auto east = tile.eastNeighbour();
```

## Building and testing

```bash
cmake -S cpp -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
ctest --test-dir build --output-on-failure
```

Tests validate against the shared cross-language golden vectors in
[`../test-vectors/`](../test-vectors). Build options: `NDSMATH_BUILD_TESTS`
(default ON at top level), `NDSMATH_INSTALL` (default ON at top level).
