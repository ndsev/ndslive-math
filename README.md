# ndsmath

`ndsmath` is a library providing mathematical utilities for NDS.Live. It offers implementations
in multiple programming languages to support various development environments.

## Overview

The `ndsmath` library covers the following aspects:

- NDS and WGS84 coordinate handling and conversion
- NDS Packed Tile IDs
- Morton code (Z-order curve) encoding and decoding

## Implementations

Currently, `ndsmath` is available in the following languages:

- C++
- Python

Future implementations are planned for:

- Java
- TypeScript

Please note that while we strive to keep all implementations synchronized with the same feature set, there may be temporary disparities between different language versions as development progresses.

## Installation

### C++

Because the C++-code is in the folder **cpp** and other parts of the repository are not required, a sparse checkout is the easiest way to add `ndsmath` to your CMakeLists.txt:

```cmake
if (NOT TARGET ndsmath)
  FetchContent_Declare(ndsmath
    GIT_REPOSITORY "https://github.com/ndsev/ndsmath.git"
    GIT_TAG        "adding-cpp"
    GIT_SHALLOW    ON)

  FetchContent_GetProperties(ndsmath)
  if(NOT ndsmath_POPULATED)
      FetchContent_Populate(ndsmath)

      # Sparse Checkout durchführen
      execute_process(
          COMMAND git sparse-checkout init --cone
          WORKING_DIRECTORY ${ndsmath_SOURCE_DIR}
      )

      execute_process(
          COMMAND git sparse-checkout set cpp
          WORKING_DIRECTORY ${ndsmath_SOURCE_DIR}
      )

      execute_process(
          COMMAND git checkout
          WORKING_DIRECTORY ${ndsmath_SOURCE_DIR}
      )
  endif()

  add_subdirectory(${ndsmath_SOURCE_DIR}/cpp ${CMAKE_BINARY_DIR}/_deps/ndsmath-build)
endif()
```

`ndsmath` depends on [glm](https://github.com/g-truc/glm.git). Make sure to add it to your project as well.

### Python

To install the Python version of `ndsmath`, use pip:

```bash
python -m pip install \
--index-url=https://pip.nds.live \
--extra-index-url=https://pypi.org/simple \
ndsmath
```

For installation instructions for other language implementations, please refer to their respective directories once they become available.

## Usage

Please refer to the README files in the language-specific directories for detailed usage instructions and examples.

## Contributing

Contributions to ndsmath are welcome! Whether you're interested in adding features, fixing bugs, or improving documentation, your help is appreciated. Please feel free to submit pull requests or open issues on the GitHub repository.
