cmake_minimum_required(VERSION 3.18)
project(hwprobe LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

option(HWPROBE_BUILD_TESTS "Build GoogleTest unit tests" ON)
option(HWPROBE_BUILD_BINDINGS "Build pybind11 Python extension" OFF)

include(FetchContent)

# ---------------------------------------------------------------------------
# Core library: cpuid + dmi
# ---------------------------------------------------------------------------
add_library(hwprobe_core STATIC
    src/cpuid.cpp
    src/dmi.cpp
)
target_include_directories(hwprobe_core PUBLIC src)
target_compile_options(hwprobe_core PRIVATE -Wall -Wextra -Wpedantic)

# ---------------------------------------------------------------------------
# Standalone CLI: `hwprobe cpuid` / `hwprobe dmi`
# ---------------------------------------------------------------------------
add_executable(hwprobe src/main.cpp)
target_link_libraries(hwprobe PRIVATE hwprobe_core)
target_compile_options(hwprobe PRIVATE -Wall -Wextra -Wpedantic)

# ---------------------------------------------------------------------------
# pybind11 binding (optional - only built when explicitly requested)
# ---------------------------------------------------------------------------
if(HWPROBE_BUILD_BINDINGS)
    FetchContent_Declare(
        pybind11
        GIT_REPOSITORY https://github.com/pybind/pybind11.git
        GIT_TAG v2.13.6
    )
    FetchContent_MakeAvailable(pybind11)
    pybind11_add_module(_hwprobe_ext src/bindings.cpp)
    target_link_libraries(_hwprobe_ext PRIVATE hwprobe_core)
endif()

# ---------------------------------------------------------------------------
# GoogleTest unit tests
# ---------------------------------------------------------------------------
if(HWPROBE_BUILD_TESTS)
    enable_testing()
    FetchContent_Declare(
        googletest
        GIT_REPOSITORY https://github.com/google/googletest.git
        GIT_TAG v1.15.2
    )
    set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(googletest)
    add_executable(hwprobe_tests
        tests/test_cpuid.cpp
        tests/test_dmi.cpp
    )
    target_link_libraries(hwprobe_tests PRIVATE hwprobe_core gtest_main)
    target_compile_options(hwprobe_tests PRIVATE -Wall -Wextra -Wpedantic)
    include(GoogleTest)
    gtest_discover_tests(hwprobe_tests)
endif()
