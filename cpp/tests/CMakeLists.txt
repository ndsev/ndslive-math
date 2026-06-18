cmake_minimum_required(VERSION 3.14)

project(ndsmath-test)

include(FetchContent)

set (USED_CATCH2_VERSION "v3.4.0")
if(TARGET Catch2::Catch2WithMain)
    if(NOT ${Catch2_VERSION} VERSION_EQUAL ${USED_CATCH2_VERSION})
        message(WARNING "Catch2 version mismatch: found ${Catch2_VERSION}, expected 3.4.0")
    endif()
else()
    FetchContent_Declare(Catch2
        GIT_REPOSITORY https://github.com/catchorg/Catch2.git
        GIT_TAG "${USED_CATCH2_VERSION}"
        GIT_SHALLOW ON)
    FetchContent_MakeAvailable(Catch2)
endif()

# Register each Catch2 TEST_CASE as its own ctest test so that a per-test
# `ctest --timeout` can pinpoint a single hanging case (e.g. the MSVC-only hang
# in test-packedtileid) instead of stalling on the whole executable.
include(Catch)

add_executable(test-packedtileid
  src/testpackedtileid.cpp)

target_link_libraries(test-packedtileid
  ndsmath
  glm::glm
  Catch2::Catch2WithMain)

add_executable(test-wgs84
  src/testwgs84.cpp)

target_link_libraries(test-wgs84
  ndsmath
  glm::glm
  Catch2::Catch2WithMain)

add_executable(test-ndsboundingbox
  src/testndsboundingbox.cpp)

target_link_libraries(test-ndsboundingbox
  ndsmath
  glm::glm
  Catch2::Catch2WithMain)

catch_discover_tests(test-packedtileid)
catch_discover_tests(test-wgs84)
catch_discover_tests(test-ndsboundingbox)
