// SPDX-License-Identifier: GPL-3.0-or-later

#include "locator/maidenhead.h"

#include <algorithm>
#include <cmath>
#include <limits>

namespace locator {
namespace {

constexpr int kUnitsPerField = 240;
constexpr int kUnitsPerSquare = 24;
constexpr int kWorldUnits = 18 * kUnitsPerField;

}  // namespace

std::optional<std::string> maidenhead_6(double latitude_degrees, double longitude_degrees) {
    if (!std::isfinite(latitude_degrees) || !std::isfinite(longitude_degrees) ||
        latitude_degrees < -90.0 || latitude_degrees > 90.0 || longitude_degrees < -180.0 ||
        longitude_degrees > 180.0) {
        return std::nullopt;
    }

    // Maidenhead divides the half-open world rectangle [-90, 90) × [-180, 180).
    // These rules make its mathematically closed API boundaries deterministic.
    const double latitude = latitude_degrees == 90.0
                                ? std::nextafter(90.0, -std::numeric_limits<double>::infinity())
                                : latitude_degrees;
    const double longitude = longitude_degrees == 180.0 ? -180.0 : longitude_degrees;
    // Convert directly to the finest six-character lattice. This avoids
    // accumulating floating-point error while repeatedly subtracting field
    // and square widths at exact subsquare boundaries.
    const int longitude_units = std::clamp(
        static_cast<int>(std::floor((longitude + 180.0) * 12.0)), 0, kWorldUnits - 1);
    const int latitude_units = std::clamp(
        static_cast<int>(std::floor((latitude + 90.0) * 24.0)), 0, kWorldUnits - 1);
    const int longitude_field = longitude_units / kUnitsPerField;
    const int latitude_field = latitude_units / kUnitsPerField;
    const int longitude_square = (longitude_units / kUnitsPerSquare) % 10;
    const int latitude_square = (latitude_units / kUnitsPerSquare) % 10;
    const int longitude_subsquare = longitude_units % kUnitsPerSquare;
    const int latitude_subsquare = latitude_units % kUnitsPerSquare;

    std::string result(6, 'A');
    result[0] = static_cast<char>('A' + longitude_field);
    result[1] = static_cast<char>('A' + latitude_field);
    result[2] = static_cast<char>('0' + longitude_square);
    result[3] = static_cast<char>('0' + latitude_square);
    result[4] = static_cast<char>('A' + longitude_subsquare);
    result[5] = static_cast<char>('A' + latitude_subsquare);
    return result;
}

}  // namespace locator
