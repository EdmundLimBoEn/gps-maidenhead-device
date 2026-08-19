// SPDX-License-Identifier: GPL-3.0-or-later

#pragma once

#include <optional>
#include <cstdint>
#include <string>
#include <string_view>

namespace locator {

struct UtcTime {
    int hour{};
    int minute{};
    int second{};
    int centisecond{};

    [[nodiscard]] bool operator==(const UtcTime&) const = default;
};

struct UtcDate {
    int year{};
    int month{};
    int day{};

    [[nodiscard]] bool operator==(const UtcDate&) const = default;
};

struct Position {
    double latitude_degrees{};
    double longitude_degrees{};
};

enum class NmeaKind {
    rmc,
    gga,
};

enum class NmeaError {
    none,
    empty,
    too_long,
    malformed,
    unsupported_sentence,
    checksum_missing,
    checksum_invalid,
    fields_missing,
    invalid_time,
    invalid_date,
    invalid_position,
};

struct NmeaSentence {
    NmeaKind kind{};
    bool receiver_fix_valid{};
    std::optional<Position> position{};
    std::optional<UtcTime> utc_time{};
    std::optional<UtcDate> utc_date{};
    std::uint8_t fix_quality{0};
    std::uint8_t satellites_used{0};
};

struct ParseResult {
    NmeaError error{NmeaError::none};
    std::optional<NmeaSentence> sentence{};

    [[nodiscard]] bool valid() const { return error == NmeaError::none && sentence.has_value(); }
};

// Parses one complete, checksum-protected RMC or GGA sentence. The parser
// deliberately does not accept partial UART fragments or sentences with a
// missing checksum.
[[nodiscard]] ParseResult parse_nmea_sentence(std::string_view line);

struct CurrentFix {
    Position position{};
    UtcTime utc_time{};
    UtcDate utc_date{};
    std::uint8_t fix_quality{0};
    std::uint8_t satellites_used{0};
};

// Requires matching, receiver-valid RMC and GGA reports. It prevents a valid
// status sentence from being combined with stale or contradictory position
// data from another epoch.
class FixAccumulator {
  public:
    [[nodiscard]] std::optional<CurrentFix> ingest(const NmeaSentence& sentence);
    void clear();

  private:
    std::optional<NmeaSentence> latest_rmc_{};
};

}  // namespace locator
