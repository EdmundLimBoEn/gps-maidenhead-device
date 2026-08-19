#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Compile the RP2040 sources against a declaration-only Pico SDK facade. This
# is a fast API/syntax gate for hosts that do not have the full SDK installed;
# release builds must still use POCKET_LOCATOR_BUILD_RP2040 with the real SDK.
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
stub_include="$repo_root/firmware/tests/pico_stub/include"
firmware_include="$repo_root/firmware/include"

g++ -std=c++20 -Wall -Wextra -Wpedantic -Werror -fsyntax-only \
  -I"$stub_include" -I"$firmware_include" \
  "$repo_root/firmware/src/maidenhead.cpp" \
  "$repo_root/firmware/src/nmea.cpp" \
  "$repo_root/firmware/src/layout.cpp" \
  "$repo_root/firmware/src/display/format.cpp" \
  "$repo_root/firmware/src/time/zone_table.cpp" \
  "$repo_root/firmware/src/app/check_session.cpp" \
  "$repo_root/firmware/src/config/config.cpp" \
  "$repo_root/firmware/src/usb/protocol.cpp" \
  "$repo_root/firmware/src/board/rp2040_board.cpp" \
  "$repo_root/firmware/src/board/buttons.cpp" \
  "$repo_root/firmware/src/board/power.cpp" \
  "$repo_root/firmware/src/board/bootloader.cpp" \
  "$repo_root/firmware/src/display/hd44780.cpp" \
  "$repo_root/firmware/src/gnss/uart_gnss.cpp" \
  "$repo_root/firmware/src/storage/flash_config_store.cpp" \
  "$repo_root/firmware/src/device/main.cpp"
