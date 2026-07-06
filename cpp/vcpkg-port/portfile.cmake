# vcpkg port for ndsmath (the C++ implementation of ndslive-math).
#
# RELEASE CHECKLIST (see README.md in this directory):
#   1. Bump "version" in vcpkg.json to match the release tag.
#   2. Set REF to the release tag (the template uses "v${VERSION}").
#   3. Replace the SHA512 placeholder with the real archive hash. The easiest
#      way: set it to "0", run `vcpkg install ndsmath --overlay-ports=...`, and
#      copy the actual hash vcpkg prints back into this file.

vcpkg_from_github(
    OUT_SOURCE_PATH SOURCE_PATH
    REPO ndsev/ndslive-math
    REF "v${VERSION}"
    SHA512 e898495604fcd52dc50af9734f9696ddc6a818db23b2440af34130cef27fd223a044a23ef4225c8d331a1b6540872879de91ed94c56ecfdf4702f2f045f3cf72
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
