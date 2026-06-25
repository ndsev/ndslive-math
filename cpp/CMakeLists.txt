cmake_minimum_required(VERSION 3.14.0)

# Version must match the release tag (vX.Y.Z) and cpp/vcpkg-port/vcpkg.json.
project(ndsmath VERSION 0.5.2 LANGUAGES CXX)

set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(GNUInstallDirs)

# Top-level detection (PROJECT_IS_TOP_LEVEL requires CMake >= 3.21).
if(CMAKE_VERSION VERSION_GREATER_EQUAL 3.21)
  set(_ndsmath_is_top ${PROJECT_IS_TOP_LEVEL})
elseif(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
  set(_ndsmath_is_top ON)
else()
  set(_ndsmath_is_top OFF)
endif()

option(NDSMATH_BUILD_TESTS "Build ndsmath tests" ${_ndsmath_is_top})
option(NDSMATH_INSTALL "Generate ndsmath install + package-config rules" ${_ndsmath_is_top})
option(NDSMATH_COVERAGE "Instrument the library and tests for coverage (gcov/llvm-cov)" OFF)

# --- GLM (public dependency) -----------------------------------------------
# Prefer a packaged/system GLM (vcpkg, find_package); fall back to FetchContent
# so the standalone / FetchContent consumption documented in the README keeps
# working without any package manager.
set(USED_GLM_VERSION "1.0.1")
set(_ndsmath_glm_via_fetchcontent OFF)
if(TARGET glm::glm)
  # Provided by a parent project; nothing to do.
else()
  find_package(glm CONFIG QUIET)
  if(NOT glm_FOUND)
    include(FetchContent)
    FetchContent_Declare(glm
      GIT_REPOSITORY "https://github.com/g-truc/glm.git"
      GIT_TAG        ${USED_GLM_VERSION}
      GIT_SHALLOW    ON)
    FetchContent_MakeAvailable(glm)
    set(_ndsmath_glm_via_fetchcontent ON)
  endif()
endif()

# Install/export requires GLM to be a findable package (its imported target must
# be reachable by consumers). A FetchContent'd GLM is not installed, so an export
# referencing it cannot be generated — disable install in that case. Packaged
# builds (e.g. vcpkg) provide GLM via find_package, where install works.
if(NDSMATH_INSTALL AND _ndsmath_glm_via_fetchcontent)
  message(STATUS
    "ndsmath: GLM came from FetchContent; disabling NDSMATH_INSTALL. "
    "For a packaged/installable build, provide GLM via find_package (e.g. vcpkg).")
  set(NDSMATH_INSTALL OFF)
endif()

# --- Library ----------------------------------------------------------------
# Respect BUILD_SHARED_LIBS when the consumer (e.g. vcpkg) sets it; otherwise
# default to SHARED to preserve historical behavior.
if(NOT DEFINED BUILD_SHARED_LIBS)
  set(_ndsmath_lib_type SHARED)
endif()

add_library(ndsmath ${_ndsmath_lib_type}
  src/mortoncode.cpp
  src/packedtileid.cpp
  src/polygontriangulation.cpp

  include/ndsmath/consts.h
  include/ndsmath/mortoncode.h
  include/ndsmath/ndsboundingbox.h
  include/ndsmath/packedtileid.h
  include/ndsmath/polygon.h
  include/ndsmath/polygontriangulation.h
  include/ndsmath/wgs84.h
  include/ndsmath/wgs84polygon.h
  include/ndsmath/wgs84aabb.h)

# Namespaced alias so FetchContent/add_subdirectory consumers can link the same
# target name as installed consumers (ndsmath::ndsmath).
add_library(ndsmath::ndsmath ALIAS ndsmath)

target_include_directories(ndsmath
  PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include/ndsmath
  PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)

target_link_libraries(ndsmath PUBLIC glm::glm)

# Public headers use C++20 (concepts/requires), so consumers must compile as
# C++20 too. PUBLIC propagates the requirement through the exported interface.
target_compile_features(ndsmath PUBLIC cxx_std_20)

# Coverage instrumentation — opt-in, CI only (never installed). PUBLIC so the
# test targets that link ndsmath are instrumented too, capturing the header-only
# code (wgs84.h, ndsboundingbox.h, …) where it is actually exercised.
if(NDSMATH_COVERAGE AND NOT MSVC)
  target_compile_options(ndsmath PUBLIC --coverage -O0 -g)
  target_link_options(ndsmath PUBLIC --coverage)
endif()

set_target_properties(ndsmath PROPERTIES
  VERSION ${PROJECT_VERSION}
  SOVERSION ${PROJECT_VERSION_MAJOR})

# --- Tests ------------------------------------------------------------------
if(NDSMATH_BUILD_TESTS)
  enable_testing()
  add_subdirectory(tests)
endif()

# --- Install / package config ----------------------------------------------
if(NDSMATH_INSTALL)
  include(CMakePackageConfigHelpers)

  install(TARGETS ndsmath
    EXPORT ndsmath-targets
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    INCLUDES DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})

  install(DIRECTORY include/ndsmath
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})

  install(EXPORT ndsmath-targets
    FILE ndsmath-targets.cmake
    NAMESPACE ndsmath::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/ndsmath)

  configure_package_config_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/cmake/ndsmath-config.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/ndsmath-config.cmake
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/ndsmath)

  write_basic_package_version_file(
    ${CMAKE_CURRENT_BINARY_DIR}/ndsmath-config-version.cmake
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion)

  install(FILES
    ${CMAKE_CURRENT_BINARY_DIR}/ndsmath-config.cmake
    ${CMAKE_CURRENT_BINARY_DIR}/ndsmath-config-version.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/ndsmath)
endif()
