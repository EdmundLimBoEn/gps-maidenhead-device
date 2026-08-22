// SPDX-License-Identifier: GPL-3.0-or-later

#include "locator/nmea.h"

#include <algorithm>
#include <charconv>
#include <cmath>
#include <cstddef>
#include <cstdlib>
#include <limits>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

namespace locator {
namespace {

constexpr std::size_t kMaximumSentenceBytes = 256;
constexpr double kMaximumPairedPositionDifferenceDegrees = 0.0001;

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
    if (text.empty() || !std::all_of(text.begin(), text.end(), [](unsigned char value) {
            return value >= '0' && value <= '9';
        })) {
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
    const auto dot = text.find('.');
    const auto whole = dot == std::string_view::npos ? text : text.substr(0, dot);
    const auto fraction = dot == std::string_view::npos ? std::string_view{} : text.substr(dot + 1U);
    const auto digits = [](std::string_view value) {
        return !value.empty() && std::all_of(value.begin(), value.end(), [](unsigned char character) {
            return character >= '0' && character <= '9';
        });
    };
    if (!digits(whole) || (dot != std::string_view::npos && !digits(fraction)) ||
        (dot != std::string_view::npos && text.find('.', dot + 1U) != std::string_view::npos)) {
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
        if (fraction.empty() || fraction.size() > 3U ||
            !std::all_of(fraction.begin(), fraction.end(), [](unsigned char value) {
                return value >= '0' && value <= '9';
            })) {
            return std::nullopt;
        }
        centisecond = (fraction[0] - '0') * 10;
        if (fraction.size() >= 2U) centisecond += fraction[1] - '0';
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
    if (raw.size() < degree_digits + 4U || raw[degree_digits] < '0' || raw[degree_digits] > '9' ||
        raw[degree_digits + 1U] < '0' || raw[degree_digits + 1U] > '9' ||
        raw[degree_digits + 2U] != '.') {
        return std::nullopt;
    }
    int degrees = 0;
    double minutes = 0.0;
    if (!parse_integer(raw.substr(0, degree_digits), degrees) ||
        !parse_decimal(raw.substr(degree_digits), minutes) || minutes < 0.0 || minutes >= 60.0) {
        return std::nullopt;
    }
    const int maximum_degrees = latitude ? 90 : 180;
    if (degrees < 0 || degrees > maximum_degrees || (degrees == maximum_degrees && minutes != 0.0)) {
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
    if (fields.empty() || fields[0].size() != 5U || fields[0][0] < 'A' || fields[0][0] > 'Z' ||
        fields[0][1] < 'A' || fields[0][1] > 'Z') {
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
        // Optional FAA mode indicators E/M/S represent estimated, manual,
        // or simulated positions and are not current live GNSS fixes.
        if (sentence.receiver_fix_valid && fields.size() > 12U && !fields[12].empty() &&
            fields[12] != "A" && fields[12] != "D" && fields[12] != "R" &&
            fields[12] != "F" && fields[12] != "P") {
            sentence.receiver_fix_valid = false;
        }
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
        if (fields[6].size() != 1U || !parse_integer(fields[6], quality) || quality < 0) {
            result.error = NmeaError::malformed;
            return result;
        }
        // NMEA qualities 6–8 are estimated/dead-reckoning, manual, and
        // simulation modes rather than receiver-declared live 2D/3D fixes.
        sentence.receiver_fix_valid = quality > 0 && quality <= 5;
        if (quality > std::numeric_limits<std::uint8_t>::max()) {
            result.error = NmeaError::malformed;
            return result;
        }
        sentence.fix_quality = static_cast<std::uint8_t>(quality);
        int satellites = 0;
        if (fields[7].size() != 2U || !parse_integer(fields[7], satellites) || satellites < 0 ||
            satellites > std::numeric_limits<std::uint8_t>::max()) {
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

std::optional<NmeaFrame> NmeaLineFramer::push(char byte) {
    if (byte == '\r') return std::nullopt;
    if (discarding_) {
        if (byte == '\n') discarding_ = false;
        return std::nullopt;
    }
    if (byte == '\n') {
        if (buffer_.empty()) return std::nullopt;
        NmeaFrame frame{NmeaFrameKind::Complete, std::move(buffer_)};
        buffer_.clear();
        return frame;
    }
    if (buffer_.size() >= maximum_bytes_) {
        buffer_.clear();
        discarding_ = true;
        return NmeaFrame{NmeaFrameKind::Overlong, {}};
    }
    buffer_.push_back(byte);
    return std::nullopt;
}

void NmeaLineFramer::reset() {
    buffer_.clear();
    discarding_ = false;
}

FixIngestResult FixAccumulator::ingest(const NmeaSentence& sentence) {
    if (!sentence.receiver_fix_valid) {
        clear_pending();
        return {{}, true};
    }
    if (sentence.kind == NmeaKind::rmc) {
        if (!sentence.position || !sentence.utc_time || !sentence.utc_date) {
            clear_pending();
            return {{}, true};
        }
        latest_rmc_ = sentence;
    } else {
        if (!sentence.position || !sentence.utc_time) {
            clear_pending();
            return {{}, true};
        }
        latest_gga_ = sentence;
    }
    if (!latest_rmc_ || !latest_gga_ || !latest_rmc_->position || !latest_gga_->position ||
        !latest_rmc_->utc_time || !latest_gga_->utc_time || !latest_rmc_->utc_date) {
        return {};
    }
    if (*latest_rmc_->utc_time != *latest_gga_->utc_time) {
        return {};
    }
    if (!positions_agree(*latest_rmc_->position, *latest_gga_->position)) {
        clear_pending();
        return {{}, true};
    }
    const CurrentFix fix{*latest_rmc_->position, *latest_rmc_->utc_time, *latest_rmc_->utc_date,
                         latest_gga_->fix_quality, latest_gga_->satellites_used};
    const auto epoch_key = [](const CurrentFix& value) {
        return std::tuple{value.utc_date.year, value.utc_date.month, value.utc_date.day,
                          value.utc_time.hour, value.utc_time.minute, value.utc_time.second,
                          value.utc_time.centisecond};
    };
    if (last_emitted_fix_ && epoch_key(fix) <= epoch_key(*last_emitted_fix_)) {
        clear_pending();
        return {{}, true};
    }
    // Each epoch can produce at most one fix and can never be reused later.
    last_emitted_fix_ = fix;
    clear_pending();
    return {fix, false};
}

void FixAccumulator::clear_pending() {
    latest_rmc_.reset();
    latest_gga_.reset();
}

void FixAccumulator::clear() {
    clear_pending();
    last_emitted_fix_.reset();
}

}  // namespace locator
