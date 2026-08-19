// SPDX-License-Identifier: GPL-3.0-or-later
#include "pocket_locator/board/power.hpp"

#include <initializer_list>

#include "hardware/gpio.h"

namespace pocket_locator::board {

void PowerHold::init() {
    gpio_init(pins_.power_hold);
    gpio_set_dir(pins_.power_hold, GPIO_OUT);
    // Do not retain a short LOCATE press. USB VBUS can still power the MCU.
    gpio_put(pins_.power_hold, false);
    for (const std::uint8_t pin : {pins_.vbus_sense, pins_.charger_active}) {
        gpio_init(pin);
        gpio_set_dir(pin, GPIO_IN);
    }
}

void PowerHold::assert_hold() { gpio_put(pins_.power_hold, true); }

void PowerHold::release() {
    gpio_put(pins_.power_hold, false);
}

bool PowerHold::usb_present() const {
    return gpio_get(pins_.vbus_sense);
}

bool PowerHold::charger_active() const {
    // The selected charger exposes an open-drain, active-low CHG status pin.
    return !gpio_get(pins_.charger_active);
}

}  // namespace pocket_locator::board
