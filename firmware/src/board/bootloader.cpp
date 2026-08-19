// SPDX-License-Identifier: GPL-3.0-or-later
#include "pocket_locator/board/bootloader.hpp"

#include "pico/bootrom.h"
#include "pico/stdlib.h"

namespace pocket_locator::board {

[[noreturn]] void reboot_to_bootloader() {
    reset_usb_boot(0, 0);
    while (true) {
        tight_loop_contents();
    }
}

}  // namespace pocket_locator::board
