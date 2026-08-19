// SPDX-License-Identifier: GPL-3.0-or-later

#pragma once

#include <optional>
#include <string>

namespace locator {

// Converts a WGS-84 coordinate to an uppercase, six-character Maidenhead
// locator. Longitude +180 is normalized to -180; latitude +90 is represented
// by the last addressable subsquare. Invalid/non-finite coordinates are
// rejected rather than silently coerced.
[[nodiscard]] std::optional<std::string> maidenhead_6(double latitude_degrees,
                                                       double longitude_degrees);

}  // namespace locator
