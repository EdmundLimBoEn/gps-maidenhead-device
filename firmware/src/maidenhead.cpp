// SPDX-License-Identifier: GPL-3.0-or-later

#include "locator/maidenhead.h"

#include <algorithm>
#include <cmath>
#include <limits>

namespace locator {
namespace {

constexpr double kFieldLongitudeDegrees = 20.0;
constexpr double kFieldLatitudeDegrees = 10.0;
constexpr double kSquareLongitudeDegrees = 2.0;
constexpr double kSquareLatitudeDegrees = 1.0;
constexpr double kSubsquareLongitudeDegrees = kSquareLongitudeDegrees / 24.0;
constexpr double kSubsquareLatitudeDegrees = kSquareLatitudeDegrees / 24.0;

int bounded_floor_index(double value, double unit, int count) {
    const auto raw = static_cast<int>(std::floor(value / unit));
    return std::clamp(raw, 0, count - 1);
}

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
    const double adjusted_latitude = latitude + 90.0;
    const double adjusted_longitude = longitude + 180.0;

    const int longitude_field = bounded_floor_index(adjusted_longitude, kFieldLongitudeDegrees, 18);
    const int latitude_field = bounded_floor_index(adjusted_latitude, kFieldLatitudeDegrees, 18);
    const double longitude_after_field = adjusted_longitude - longitude_field * kFieldLongitudeDegrees;
    const double latitude_after_field = adjusted_latitude - latitude_field * kFieldLatitudeDegrees;
    const int longitude_square = bounded_floor_index(longitude_after_field, kSquareLongitudeDegrees, 10);
    const int latitude_square = bounded_floor_index(latitude_after_field, kSquareLatitudeDegrees, 10);
    const double longitude_after_square = longitude_after_field - longitude_square * kSquareLongitudeDegrees;
    const double latitude_after_square = latitude_after_field - latitude_square * kSquareLatitudeDegrees;
    const int longitude_subsquare =
        bounded_floor_index(longitude_after_square, kSubsquareLongitudeDegrees, 24);
    const int latitude_subsquare = bounded_floor_index(latitude_after_square, kSubsquareLatitudeDegrees, 24);

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
