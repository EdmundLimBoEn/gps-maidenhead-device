// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <cstdint>
#include <optional>

#include "locator/nmea.h"
#include "pocket_locator/board/pins.hpp"

namespace pocket_locator::gnss {

// Allow the switched GNSS rail to rise before the MCU drives module I/O.
inline constexpr std::uint32_t kGnssPowerRailSettleUs = 5'000U;

struct PollResult {
    std::optional<locator::CurrentFix> fix{};
    bool invalid_fix{false};
    bool invalid_after_fix{false};
};

class UartGnss {
public:
    explicit UartGnss(board::PinMap pins = board::kDefaultPins, std::uint32_t baud = 9'600);
    void init();
    void set_enabled(bool enabled);
    [[nodiscard]] bool enabled() const { return enabled_; }
    [[nodiscard]] PollResult poll();

private:
    board::PinMap pins_;
    std::uint32_t baud_;
    bool enabled_{false};
    locator::NmeaLineFramer framer_{127};
    locator::FixAccumulator accumulator_{};
};

}  // namespace pocket_locator::gnss
