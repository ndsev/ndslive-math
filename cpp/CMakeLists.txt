cmake_minimum_required(VERSION 3.14.0)
project(ndsmath)

set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(ndsmath SHARED
  src/mortoncode.cpp
  src/packedtileid.cpp

  include/ndsmath/mortoncode.h
  include/ndsmath/packedtileid.h
  include/ndsmath/wgs84.h
  include/ndsmath/wgs84polygon.h
  include/ndsmath/wgs84aabb.h)

target_include_directories(ndsmath
  PRIVATE include/ndsmath
  PUBLIC include
  PUBLIC ${CMAKE_CURRENT_BINARY_DIR}/version/)

target_link_libraries(ndsmath
  PUBLIC
    glm::glm)
