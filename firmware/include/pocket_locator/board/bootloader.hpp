// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

namespace pocket_locator::board {

// Transfers directly to the immutable RP2040 ROM USB bootloader.  The
// physical BOOTSEL switch remains an independent recovery path.
[[noreturn]] void reboot_to_bootloader();

}  // namespace pocket_locator::board
