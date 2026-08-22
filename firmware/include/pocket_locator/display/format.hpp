// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <cstdint>
#include <string>

#include "locator/nmea.h"
#include "pocket_locator/config/config.hpp"

namespace pocket_locator::display {

struct FormattedFixScreen {
    std::string top_row;
    std::string bottom_row;
    bool timezone_refresh_required{false};
};

// Converts a live GNSS UTC fix through the persisted IANA transition table
// and expands the validated blocks into the exact LCD rows. Battery glyphs
// use CGRAM slots 0..4 and are therefore intentionally non-printable bytes.
[[nodiscard]] FormattedFixScreen format_fix_screen(const config::Settings& settings, std::string_view grid,
                                                    const locator::CurrentFix& fix, std::uint8_t battery_percent,
                                                    bool charging, std::uint64_t elapsed_seconds = 0);

}  // namespace pocket_locator::display
