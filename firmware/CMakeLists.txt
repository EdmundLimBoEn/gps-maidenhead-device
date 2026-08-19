cmake_minimum_required(VERSION 3.20)

project(maidenhead_pocket_locator_host_tests LANGUAGES CXX)

option(POCKET_LOCATOR_BUILD_HOST_TESTS "Build deterministic host tests" ON)

add_library(pocket_locator_core
    src/maidenhead.cpp
    src/nmea.cpp
    src/layout.cpp
    src/time/zone_table.cpp
    src/app/check_session.cpp
    src/config/config.cpp
    src/usb/protocol.cpp
)

target_include_directories(pocket_locator_core PUBLIC include)
target_compile_features(pocket_locator_core PUBLIC cxx_std_20)

if(MSVC)
    target_compile_options(pocket_locator_core PRIVATE /W4 /permissive-)
else()
    target_compile_options(pocket_locator_core PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

if(POCKET_LOCATOR_BUILD_HOST_TESTS)
    enable_testing()

    add_executable(pocket_locator_host_tests
        tests/test_main.cpp
        tests/check_session_tests.cpp
        tests/config_tests.cpp
        tests/locator_tests.cpp
        tests/protocol_tests.cpp
        tests/time_tests.cpp
    )
    target_link_libraries(pocket_locator_host_tests PRIVATE pocket_locator_core)
    target_compile_features(pocket_locator_host_tests PRIVATE cxx_std_20)

    if(MSVC)
        target_compile_options(pocket_locator_host_tests PRIVATE /W4 /permissive-)
    else()
        target_compile_options(pocket_locator_host_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()

    add_test(NAME pocket_locator_host_tests COMMAND pocket_locator_host_tests)
endif()
