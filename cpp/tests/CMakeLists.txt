cmake_minimum_required(VERSION 3.14)

project(ndsmath-test)

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

add_test(NAME test-packedtileid
  COMMAND "$<TARGET_FILE:test-packedtileid>")

add_test(NAME test-wgs84
  COMMAND "$<TARGET_FILE:test-wgs84>")
