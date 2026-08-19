// SPDX-License-Identifier: GPL-3.0-or-later

#include "locator/nmea.h"

#include <charconv>
#include <cmath>
#include <cstddef>
#include <cstdlib>
#include <limits>
#include <string>
#include <vector>

namespace locator {
namespace {

constexpr std::size_t kMaximumSentenceBytes = 256;
constexpr double kMaximumPairedPositionDifferenceDegrees = 0.001;

std::vector<std::string_view> split_fields(std::string_view payload) {
    std::vector<std::string_view> fields;
    std::size_t start = 0;
    while (start <= payload.size()) {
        const std::size_t comma = payload.find(',', start);
        if (comma == std::string_view::npos) {
            fields.push_back(payload.substr(start));
            break;
        }
        fields.push_back(payload.substr(start, comma - start));
        start = comma + 1;
    }
    return fields;
}

bool parse_integer(std::string_view text, int& result) {
    if (text.empty()) {
        return false;
    }
    const char* const begin = text.data();
    const char* const end = begin + text.size();
    const auto [pointer, error] = std::from_chars(begin, end, result);
    return error == std::errc{} && pointer == end;
}

bool parse_decimal(std::string_view text, double& result) {
    if (text.empty()) {
        return false;
    }
    std::string copy{text};
    char* end = nullptr;
    result = std::strtod(copy.c_str(), &end);
    return end == copy.c_str() + copy.size() && std::isfinite(result);
}

std::optional<UtcTime> parse_time(std::string_view text) {
    if (text.size() < 6U) {
        return std::nullopt;
    }
    int hour = 0;
    int minute = 0;
    int second = 0;
    if (!parse_integer(text.substr(0, 2), hour) || !parse_integer(text.substr(2, 2), minute) ||
        !parse_integer(text.substr(4, 2), second) || hour > 23 || minute > 59 || second > 60) {
        return std::nullopt;
    }
    int centisecond = 0;
    if (text.size() > 6U) {
        if (text[6] != '.') {
            return std::nullopt;
        }
        const std::string_view fraction = text.substr(7);
        if (fraction.empty() || fraction.size() > 2U) {
            return std::nullopt;
        }
        if (!parse_integer(fraction, centisecond)) {
            return std::nullopt;
        }
        if (fraction.size() == 1U) {
            centisecond *= 10;
        }
    }
    return UtcTime{hour, minute, second, centisecond};
}

std::optional<UtcDate> parse_date(std::string_view text) {
    if (text.size() != 6U) {
        return std::nullopt;
    }
    int day = 0;
    int month = 0;
    int year_suffix = 0;
    if (!parse_integer(text.substr(0, 2), day) || !parse_integer(text.substr(2, 2), month) ||
        !parse_integer(text.substr(4, 2), year_suffix) || day < 1 || month < 1 || month > 12) {
        return std::nullopt;
    }
    // NMEA carries a two-digit year. This pivot supports recorded historical
    // data while retaining the useful 2000–2079 device range.
    const int year = year_suffix >= 80 ? 1900 + year_suffix : 2000 + year_suffix;
    constexpr int days_in_month[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    const bool leap_year = (year % 4 == 0 && year % 100 != 0) || year % 400 == 0;
    const int maximum_day = month == 2 && leap_year ? 29 : days_in_month[month - 1];
    if (day > maximum_day) {
        return std::nullopt;
    }
    return UtcDate{year, month, day};
}

std::optional<double> parse_coordinate(std::string_view raw, std::string_view hemisphere, bool latitude) {
    if (raw.empty() || hemisphere.size() != 1U) {
        return std::nullopt;
    }
    const std::size_t degree_digits = latitude ? 2U : 3U;
    if (raw.size() <= degree_digits) {
        return std::nullopt;
    }
    int degrees = 0;
    double minutes = 0.0;
    if (!parse_integer(raw.substr(0, degree_digits), degrees) ||
        !parse_decimal(raw.substr(degree_digits), minutes) || minutes < 0.0 || minutes >= 60.0) {
        return std::nullopt;
    }
    const int maximum_degrees = latitude ? 90 : 180;
    if (degrees > maximum_degrees || (degrees == maximum_degrees && minutes != 0.0)) {
        return std::nullopt;
    }
    const char sign_letter = hemisphere.front();
    const bool negative = latitude ? sign_letter == 'S' : sign_letter == 'W';
    const bool positive = latitude ? sign_letter == 'N' : sign_letter == 'E';
    if (!negative && !positive) {
        return std::nullopt;
    }
    const double value = static_cast<double>(degrees) + minutes / 60.0;
    return negative ? -value : value;
}

std::optional<Position> parse_position(const std::vector<std::string_view>& fields,
                                       std::size_t latitude_index,
                                       std::size_t longitude_index) {
    if (longitude_index + 1U >= fields.size() || latitude_index + 1U >= fields.size()) {
        return std::nullopt;
    }
    const auto latitude = parse_coordinate(fields[latitude_index], fields[latitude_index + 1U], true);
    const auto longitude = parse_coordinate(fields[longitude_index], fields[longitude_index + 1U], false);
    if (!latitude || !longitude) {
        return std::nullopt;
    }
    return Position{*latitude, *longitude};
}

int hex_value(char value) {
    if (value >= '0' && value <= '9') {
        return value - '0';
    }
    if (value >= 'A' && value <= 'F') {
        return value - 'A' + 10;
    }
    if (value >= 'a' && value <= 'f') {
        return value - 'a' + 10;
    }
    return -1;
}

bool positions_agree(const Position& first, const Position& second) {
    return std::abs(first.latitude_degrees - second.latitude_degrees) <=
               kMaximumPairedPositionDifferenceDegrees &&
           std::abs(first.longitude_degrees - second.longitude_degrees) <=
               kMaximumPairedPositionDifferenceDegrees;
}

}  // namespace

ParseResult parse_nmea_sentence(std::string_view line) {
    ParseResult result{};
    if (line.empty()) {
        result.error = NmeaError::empty;
        return result;
    }
    if (line.size() > kMaximumSentenceBytes) {
        result.error = NmeaError::too_long;
        return result;
    }
    if (line.ends_with("\r\n")) {
        line.remove_suffix(2);
    } else if (line.ends_with('\n') || line.ends_with('\r')) {
        line.remove_suffix(1);
    }
    if (line.size() < 7U || line.front() != '$') {
        result.error = NmeaError::malformed;
        return result;
    }
    const std::size_t star = line.rfind('*');
    if (star == std::string_view::npos) {
        result.error = NmeaError::checksum_missing;
        return result;
    }
    if (star + 3U != line.size()) {
        result.error = NmeaError::malformed;
        return result;
    }
    const int upper_nibble = hex_value(line[star + 1U]);
    const int lower_nibble = hex_value(line[star + 2U]);
    if (upper_nibble < 0 || lower_nibble < 0) {
        result.error = NmeaError::checksum_invalid;
        return result;
    }
    unsigned char checksum = 0;
    for (std::size_t index = 1; index < star; ++index) {
        checksum ^= static_cast<unsigned char>(line[index]);
    }
    if (checksum != static_cast<unsigned char>((upper_nibble << 4) | lower_nibble)) {
        result.error = NmeaError::checksum_invalid;
        return result;
    }

    const auto fields = split_fields(line.substr(1, star - 1U));
    if (fields.empty() || fields[0].size() != 5U) {
        result.error = NmeaError::unsupported_sentence;
        return result;
    }
    const std::string_view type = fields[0].substr(2);
    NmeaSentence sentence{};
    if (type == "RMC") {
        if (fields.size() < 10U) {
            result.error = NmeaError::fields_missing;
            return result;
        }
        sentence.kind = NmeaKind::rmc;
        sentence.utc_time = parse_time(fields[1]);
        if (!sentence.utc_time) {
            result.error = NmeaError::invalid_time;
            return result;
        }
        sentence.utc_date = parse_date(fields[9]);
        if (!sentence.utc_date) {
            result.error = NmeaError::invalid_date;
            return result;
        }
        if (fields[2] != "A" && fields[2] != "V") {
            result.error = NmeaError::malformed;
            return result;
        }
        sentence.receiver_fix_valid = fields[2] == "A";
        if (sentence.receiver_fix_valid) {
            sentence.position = parse_position(fields, 3, 5);
            if (!sentence.position) {
                result.error = NmeaError::invalid_position;
                return result;
            }
        }
    } else if (type == "GGA") {
        if (fields.size() < 8U) {
            result.error = NmeaError::fields_missing;
            return result;
        }
        sentence.kind = NmeaKind::gga;
        sentence.utc_time = parse_time(fields[1]);
        if (!sentence.utc_time) {
            result.error = NmeaError::invalid_time;
            return result;
        }
        int quality = 0;
        if (!parse_integer(fields[6], quality) || quality < 0) {
            result.error = NmeaError::malformed;
            return result;
        }
        sentence.receiver_fix_valid = quality > 0;
        if (quality > std::numeric_limits<std::uint8_t>::max()) {
            result.error = NmeaError::malformed;
            return result;
        }
        sentence.fix_quality = static_cast<std::uint8_t>(quality);
        int satellites = 0;
        if (!parse_integer(fields[7], satellites) || satellites < 0 || satellites > std::numeric_limits<std::uint8_t>::max()) {
            result.error = NmeaError::malformed;
            return result;
        }
        sentence.satellites_used = static_cast<std::uint8_t>(satellites);
        if (sentence.receiver_fix_valid) {
            sentence.position = parse_position(fields, 2, 4);
            if (!sentence.position) {
                result.error = NmeaError::invalid_position;
                return result;
            }
        }
    } else {
        result.error = NmeaError::unsupported_sentence;
        return result;
    }
    result.sentence = sentence;
    return result;
}

std::optional<CurrentFix> FixAccumulator::ingest(const NmeaSentence& sentence) {
    if (sentence.kind == NmeaKind::rmc) {
        if (sentence.receiver_fix_valid && sentence.position && sentence.utc_time && sentence.utc_date) {
            latest_rmc_ = sentence;
        } else {
            latest_rmc_.reset();
        }
        return std::nullopt;
    }
    if (!sentence.receiver_fix_valid || !sentence.position || !sentence.utc_time || !latest_rmc_ ||
        !latest_rmc_->position || !latest_rmc_->utc_time || !latest_rmc_->utc_date ||
        *sentence.utc_time != *latest_rmc_->utc_time ||
        !positions_agree(*sentence.position, *latest_rmc_->position)) {
        return std::nullopt;
    }
    return CurrentFix{*latest_rmc_->position, *latest_rmc_->utc_time, *latest_rmc_->utc_date,
                      sentence.fix_quality, sentence.satellites_used};
}

void FixAccumulator::clear() {
    latest_rmc_.reset();
}

}  // namespace locator
