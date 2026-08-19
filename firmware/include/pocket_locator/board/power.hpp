// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include "pocket_locator/board/pins.hpp"

namespace pocket_locator::board {

class PowerHold {
public:
    explicit PowerHold(PinMap pins = kDefaultPins) : pins_(pins) {}
    void init();
    void assert_hold();
    void release();
    [[nodiscard]] bool usb_present() const;
    [[nodiscard]] bool charger_active() const;

private:
    PinMap pins_;
};

}  // namespace pocket_locator::board
