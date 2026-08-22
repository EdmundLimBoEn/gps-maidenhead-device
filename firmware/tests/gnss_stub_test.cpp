// SPDX-License-Identifier: GPL-3.0-or-later
#include "pocket_locator/gnss/uart_gnss.hpp"

#include "pico/stdlib.h"

int main() {
    pocket_locator::gnss::UartGnss gnss;
    gnss.init();
    gnss.set_enabled(true);
    return pico_stub::last_sleep_us == pocket_locator::gnss::kGnssPowerRailSettleUs ? 0 : 1;
}
