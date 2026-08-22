// SPDX-License-Identifier: GPL-3.0-or-later
#include "pocket_locator/board/battery.hpp"

#include "pico/stdlib.h"

int main() {
    pocket_locator::board::BatteryAdc battery;
    battery.init();
    pico_stub::last_sleep_us = 0;
    battery.begin_read();
    static_cast<void>(battery.finish_read());
    if (pico_stub::last_sleep_us != 0) return 1;
    static_cast<void>(battery.read());
    return pico_stub::last_sleep_us == pocket_locator::board::kBatteryDividerSettleUs ? 0 : 2;
}
