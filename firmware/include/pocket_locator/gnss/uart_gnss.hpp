// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>

#include "locator/nmea.h"
#include "pocket_locator/board/pins.hpp"

namespace pocket_locator::gnss {

class UartGnss {
public:
    explicit UartGnss(board::PinMap pins = board::kDefaultPins, std::uint32_t baud = 9'600);
    void init();
    void set_enabled(bool enabled);
    [[nodiscard]] bool enabled() const { return enabled_; }
    [[nodiscard]] std::optional<locator::CurrentFix> poll();

private:
    board::PinMap pins_;
    std::uint32_t baud_;
    bool enabled_{false};
    std::array<char, 128> line_{};
    std::size_t line_length_{0};
    locator::FixAccumulator accumulator_{};
};

}  // namespace pocket_locator::gnss
