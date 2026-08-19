// SPDX-License-Identifier: GPL-3.0-or-later
#include "pocket_locator/board/buttons.hpp"

#include "hardware/gpio.h"

namespace pocket_locator::board {
namespace {
[[nodiscard]] bool pressed(std::uint8_t pin) { return !gpio_get(pin); }
}

Buttons::Buttons(PinMap pins, std::uint32_t debounce_ms) : pins_(pins), debounce_ms_(debounce_ms) {}

void Buttons::init() {
    for (const std::uint8_t pin : {pins_.locate_button, pins_.off_button}) {
        gpio_init(pin);
        gpio_set_dir(pin, GPIO_IN);
        gpio_pull_up(pin);
    }
    raw_locate_ = pressed(pins_.locate_button);
    raw_off_ = pressed(pins_.off_button);
    // If LOCATE is what closed the hardware latch, firmware starts while it
    // is already held. Treat that as a debounced down-edge after init rather
    // than losing the press and immediately dropping power.
    stable_locate_ = false;
    stable_off_ = false;
    locate_held_at_boot_ = raw_locate_;
}

bool Buttons::poll(std::uint64_t now_ms, ButtonEvent& event) {
    const bool locate = pressed(pins_.locate_button);
    const bool off = pressed(pins_.off_button);
    if (locate != raw_locate_) {
        raw_locate_ = locate;
        locate_changed_ms_ = now_ms;
    }
    if (off != raw_off_) {
        raw_off_ = off;
        off_changed_ms_ = now_ms;
    }
    if (raw_locate_ != stable_locate_ && now_ms - locate_changed_ms_ >= debounce_ms_) {
        stable_locate_ = raw_locate_;
        event = {app::Button::Locate, stable_locate_, stable_locate_ && locate_held_at_boot_ ? 0U : locate_changed_ms_};
        locate_held_at_boot_ = false;
        return true;
    }
    if (raw_off_ != stable_off_ && now_ms - off_changed_ms_ >= debounce_ms_) {
        stable_off_ = raw_off_;
        event = {app::Button::Off, stable_off_, off_changed_ms_};
        return true;
    }
    return false;
}

}  // namespace pocket_locator::board
