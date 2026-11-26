# vcpkg port for ndsmath (the C++ implementation of ndslive-math).
#
# RELEASE CHECKLIST (see README.md in this directory):
#   1. Bump "version" in vcpkg.json to match the release tag.
#   2. Pin the versioned source commit; switch to "v${VERSION}" after tagging.
#   3. Whenever REF changes, replace SHA512 with the new archive hash. The easiest
#      way: set it to "0", run `vcpkg install ndsmath --overlay-ports=...`, and
#      copy the actual hash vcpkg prints back into this file.

vcpkg_from_github(
    OUT_SOURCE_PATH SOURCE_PATH
    REPO ndsev/ndslive-math
    REF a1b60d214e62e561b65e588cf814748cb32d611c
    SHA512 7a42c4fc9ce5df5c2e9dbc4dcb91c27b3332b5a67f6dcb605245f3cb31964014c11c01535435d5c736a9d3f5ea0a3a5bc80dcc02fbf3a16b0d854666b80a5e9f
    HEAD_REF main
)

# The CMake project lives in the cpp/ subdirectory of the repository.
vcpkg_cmake_configure(
    SOURCE_PATH "${SOURCE_PATH}/cpp"
    OPTIONS
        -DNDSMATH_BUILD_TESTS=OFF
        -DNDSMATH_INSTALL=ON
)

vcpkg_cmake_install()

# Move the exported package config to the vcpkg-standard location and drop the
# duplicate debug headers.
vcpkg_cmake_config_fixup(PACKAGE_NAME ndsmath CONFIG_PATH lib/cmake/ndsmath)
vcpkg_copy_pdbs()

file(REMOVE_RECURSE "${CURRENT_PACKAGES_DIR}/debug/include")

vcpkg_install_copyright(FILE_LIST "${SOURCE_PATH}/cpp/LICENSE")
file(INSTALL "${CMAKE_CURRENT_LIST_DIR}/usage" DESTINATION "${CURRENT_PACKAGES_DIR}/share/${PORT}")
