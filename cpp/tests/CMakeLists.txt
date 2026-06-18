cmake_minimum_required(VERSION 3.14)

project(ndsmath-test)

include(FetchContent)

set (USED_CATCH2_VERSION "v3.8.1")
if(TARGET Catch2::Catch2WithMain)
    if(NOT ${Catch2_VERSION} VERSION_EQUAL ${USED_CATCH2_VERSION})
        message(WARNING "Catch2 version mismatch: found ${Catch2_VERSION}, expected 3.8.1")
    endif()
else()
    FetchContent_Declare(Catch2
        GIT_REPOSITORY https://github.com/catchorg/Catch2.git
        GIT_TAG "${USED_CATCH2_VERSION}"
        GIT_SHALLOW ON)
    FetchContent_MakeAvailable(Catch2)
endif()

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

add_test(NAME test-packedtileid
  COMMAND "$<TARGET_FILE:test-packedtileid>")

add_test(NAME test-wgs84
  COMMAND "$<TARGET_FILE:test-wgs84>")

add_test(NAME test-ndsboundingbox
  COMMAND "$<TARGET_FILE:test-ndsboundingbox>")
