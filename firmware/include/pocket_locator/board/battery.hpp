// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <cstdint>

#include "pocket_locator/board/pins.hpp"

namespace pocket_locator::board {

// Rev-A uses a 100 kohm / 100 kohm divider with 100 nF at the ADC input.
// Its 50 kohm Thevenin resistance gives a 5 ms RC time constant, so wait six
// time constants after enabling the divider before taking a reading.
inline constexpr std::uint32_t kBatteryDividerTheveninOhms = 50'000U;
inline constexpr std::uint32_t kBatteryDividerCapacitanceNanofarads = 100U;
inline constexpr std::uint32_t kBatteryDividerTimeConstantUs =
    (kBatteryDividerTheveninOhms * kBatteryDividerCapacitanceNanofarads) / 1'000U;
inline constexpr std::uint32_t kBatteryDividerSettleUs = 30'000U;
static_assert(kBatteryDividerSettleUs >= 5U * kBatteryDividerTimeConstantUs);

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
    void begin_read() const;
    [[nodiscard]] BatteryReading finish_read() const;
    [[nodiscard]] BatteryReading read() const;

private:
    PinMap pins_;
    std::uint32_t divider_numerator_;
    std::uint32_t divider_denominator_;
};

}  // namespace pocket_locator::board
