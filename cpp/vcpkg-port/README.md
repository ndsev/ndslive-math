# vcpkg port for `ndsmath`

This directory holds the [vcpkg](https://vcpkg.io) port for the C++ library
(`ndsmath`, the C++ implementation of `ndslive-math`). It is kept in-repo so it
can be used as an **overlay port** today and submitted to the upstream
[`microsoft/vcpkg`](https://github.com/microsoft/vcpkg) registry once a public
release tag exists.

> **Prerequisite:** vcpkg fetches sources from a **public GitHub release tag**.
> The port can only be finalized/submitted after the repository is public and a
> `vX.Y.Z` tag has been pushed (see the release checklist below).

## Use as an overlay port (local / pre-submission)

```bash
vcpkg install ndsmath --overlay-ports=<path-to-repo>/cpp/vcpkg-port
```

Then, in your project:

```cmake
find_package(ndsmath CONFIG REQUIRED)
target_link_libraries(main PRIVATE ndsmath::ndsmath)
```

`glm` is pulled in automatically as a dependency.

## Release checklist

When cutting a release `vX.Y.Z`:

1. Set `version` in `vcpkg.json` to `X.Y.Z` (and keep `cpp/CMakeLists.txt`'s
   `project(... VERSION X.Y.Z)` in sync).
2. In `portfile.cmake`, `REF` already resolves to `v${VERSION}`; just make sure
   the tag exists.
3. Replace the `SHA512 0` placeholder with the real archive hash: set it to `0`,
   run the overlay install above, and copy the hash vcpkg reports back into
   `portfile.cmake`.
4. To publish on the public registry, open a PR to `microsoft/vcpkg` adding
   `ports/ndsmath/` (these files) and the matching `versions/` entry. Their CI
   builds the port on all triplets.

## Notes

- The CMake project lives in the repo's `cpp/` subdirectory; the portfile points
  `vcpkg_cmake_configure` there and builds with `-DNDSMATH_BUILD_TESTS=OFF`.
- The library respects `BUILD_SHARED_LIBS`, so static and dynamic triplets both
  work.
