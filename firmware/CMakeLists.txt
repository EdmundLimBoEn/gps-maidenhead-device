cmake_minimum_required(VERSION 3.20)

# The host-test build intentionally has no Pico SDK dependency.  Set
# PICO_SDK_PATH (or pass -DPOCKET_LOCATOR_BUILD_RP2040=ON) to also produce a
# UF2 from the same deterministic core.
if(DEFINED PICO_SDK_PATH AND EXISTS "${PICO_SDK_PATH}/external/pico_sdk_import.cmake")
    include("${PICO_SDK_PATH}/external/pico_sdk_import.cmake")
elseif(DEFINED ENV{PICO_SDK_PATH} AND EXISTS "$ENV{PICO_SDK_PATH}/external/pico_sdk_import.cmake")
    include("$ENV{PICO_SDK_PATH}/external/pico_sdk_import.cmake")
endif()

project(maidenhead_pocket_locator LANGUAGES C CXX ASM)

option(POCKET_LOCATOR_BUILD_HOST_TESTS "Build deterministic host tests" ON)
option(POCKET_LOCATOR_BUILD_RP2040 "Build the RP2040 firmware (requires Pico SDK)" OFF)

add_library(pocket_locator_core
    src/maidenhead.cpp
    src/nmea.cpp
    src/layout.cpp
    src/display/format.cpp
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

if(POCKET_LOCATOR_BUILD_RP2040)
    if(NOT COMMAND pico_sdk_init)
        message(FATAL_ERROR "POCKET_LOCATOR_BUILD_RP2040 requires PICO_SDK_PATH pointing to the Raspberry Pi Pico SDK")
    endif()
    pico_sdk_init()

    set(POCKET_LOCATOR_DEVICE_SOURCES
        src/device/main.cpp
        src/board/rp2040_board.cpp
        src/board/buttons.cpp
        src/board/power.cpp
        src/board/bootloader.cpp
        src/display/hd44780.cpp
        src/gnss/uart_gnss.cpp
        src/storage/flash_config_store.cpp
    )
    add_executable(pocket_locator_rp2040 ${POCKET_LOCATOR_DEVICE_SOURCES})
    target_link_libraries(pocket_locator_rp2040 PRIVATE
        pocket_locator_core
        pico_stdlib
        pico_bootrom
        hardware_adc
        hardware_flash
        hardware_pwm
        hardware_uart
        hardware_watchdog
    )
    target_compile_features(pocket_locator_rp2040 PRIVATE cxx_std_20)
    target_compile_definitions(pocket_locator_rp2040 PRIVATE
        PICO_STDIO_USB=1
        PICO_STDIO_UART=0
    )
    # Apply strict warnings only to project sources. Pico SDK sources are added
    # to this target internally and intentionally use constructs rejected by
    # -Wpedantic, so target-wide -Werror would make upstream SDK code fail.
    set_source_files_properties(${POCKET_LOCATOR_DEVICE_SOURCES} PROPERTIES
        COMPILE_OPTIONS "-Wall;-Wextra;-Wpedantic;-Werror"
    )
    pico_enable_stdio_usb(pocket_locator_rp2040 1)
    pico_enable_stdio_uart(pocket_locator_rp2040 0)
    pico_add_extra_outputs(pocket_locator_rp2040)
endif()

if(POCKET_LOCATOR_BUILD_HOST_TESTS)
    enable_testing()

    add_executable(pocket_locator_host_tests
        tests/test_main.cpp
        tests/check_session_tests.cpp
        tests/config_tests.cpp
        tests/display_tests.cpp
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
