cmake_minimum_required(VERSION 3.14)

project(ndsmath-test)

include(FetchContent)

# Header-only JSON parser for the golden-vector parity test. Replaces Catch2
# (which hung at startup on the Windows/MSVC CI runner); a header-only library
# has no test-framework runtime and no separate DLL to locate.
set(USED_JSON_VERSION "v3.11.3")
if(NOT TARGET nlohmann_json::nlohmann_json)
    FetchContent_Declare(nlohmann_json
        GIT_REPOSITORY https://github.com/nlohmann/json.git
        GIT_TAG "${USED_JSON_VERSION}"
        GIT_SHALLOW ON)
    FetchContent_MakeAvailable(nlohmann_json)
endif()

# Absolute path to the shared parity vectors, baked in at configure time.
get_filename_component(NDSMATH_REPO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../.." ABSOLUTE)

add_executable(test-units src/test-units.cpp)
target_link_libraries(test-units ndsmath glm::glm)

add_executable(test-polygon src/test-polygon.cpp)
target_link_libraries(test-polygon ndsmath glm::glm)

add_executable(test-parity src/test-parity.cpp)
target_link_libraries(test-parity ndsmath glm::glm nlohmann_json::nlohmann_json)
target_compile_definitions(test-parity PRIVATE
    PARITY_VECTORS_PATH="${NDSMATH_REPO_ROOT}/test-vectors/parity_vectors.json")

# On Windows the loader does not use rpath, so the shared ndsmath.dll must sit
# next to each test executable for it to start. Copy runtime DLLs post-build.
if(WIN32)
    foreach(t test-units test-polygon test-parity)
        add_custom_command(TARGET ${t} POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                    $<TARGET_RUNTIME_DLLS:${t}> $<TARGET_FILE_DIR:${t}>
            COMMAND_EXPAND_LISTS)
    endforeach()
endif()

add_test(NAME units COMMAND test-units)
add_test(NAME polygon COMMAND test-polygon)
add_test(NAME parity COMMAND test-parity)
