cmake_minimum_required(VERSION 3.14.0)
project(ndsmath)

include(FetchContent)

set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(ndsmath SHARED
  src/mortoncode.cpp
  src/packedtileid.cpp
  src/polygontriangulation.cpp

  include/ndsmath/mortoncode.h
  include/ndsmath/packedtileid.h
  include/ndsmath/polygontriangulation.h
  include/ndsmath/wgs84.h
  include/ndsmath/wgs84polygon.h
  include/ndsmath/wgs84aabb.h)

target_include_directories(ndsmath
  PRIVATE include/ndsmath
  PUBLIC include)

set(USED_GLM_VERSION "1.0.1")
if(TARGET glm::glm)
  if(NOT ${glm_VERSION} VERSION_EQUAL ${USED_GLM_VERSION})
    message(WARNING "glm version mismatch: found ${glm_VERSION}, expected ${USED_GLM_VERSION}")
  endif()
else()
  FetchContent_Declare(glm
    GIT_REPOSITORY "https://github.com/g-truc/glm.git"
    GIT_TAG        ${USED_GLM_VERSION}
    GIT_SHALLOW    ON)
  FetchContent_MakeAvailable(glm)
endif()

target_link_libraries(ndsmath
  PUBLIC
    glm::glm)

# Tests
enable_testing()
add_subdirectory(tests)
