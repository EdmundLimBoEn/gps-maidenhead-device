// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <cstdint>

#include "pocket_locator/app/check_session.hpp"
#include "pocket_locator/board/pins.hpp"

namespace pocket_locator::board {

struct ButtonEvent {
    app::Button button{app::Button::Locate};
    bool down{false};
    std::uint64_t pressed_at_ms{0};
};

// Polling debounce keeps the power-latch inputs deterministic and avoids an
// IRQ path that could retain POWER_HOLD after a watchdog recovery.
class Buttons {
public:
    explicit Buttons(PinMap pins = kDefaultPins, std::uint32_t debounce_ms = 25);
    void init();
    [[nodiscard]] bool poll(std::uint64_t now_ms, ButtonEvent& event);

private:
    PinMap pins_;
    std::uint32_t debounce_ms_;
    bool raw_locate_{false};
    bool raw_off_{false};
    bool stable_locate_{false};
    bool stable_off_{false};
    std::uint64_t locate_changed_ms_{0};
    std::uint64_t off_changed_ms_{0};
    bool locate_held_at_boot_{false};
};

}  // namespace pocket_locator::board
