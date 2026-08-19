// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <cstdint>

#include "pocket_locator/board/pins.hpp"

namespace pocket_locator::board {

struct BatteryReading {
    std::uint16_t raw{};
    std::uint16_t millivolts{};
    std::uint8_t percent{};
    std::int16_t temperature_centi_celsius{};
};

class BatteryAdc {
public:
    // divider_numerator/divider_denominator describe Vbat = Vadc * ratio.
    BatteryAdc(PinMap pins = kDefaultPins, std::uint32_t divider_numerator = 2,
               std::uint32_t divider_denominator = 1);
    void init();
    [[nodiscard]] BatteryReading read() const;

private:
    PinMap pins_;
    std::uint32_t divider_numerator_;
    std::uint32_t divider_denominator_;
};

}  // namespace pocket_locator::board
