// SPDX-License-Identifier: GPL-3.0-or-later

#pragma once

#include <optional>
#include <cstdint>
#include <cstddef>
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

enum class NmeaFrameKind { Complete, Overlong };

struct NmeaFrame {
    NmeaFrameKind kind{NmeaFrameKind::Complete};
    std::string payload{};
};

class NmeaLineFramer {
public:
    explicit NmeaLineFramer(std::size_t maximum_bytes = 127) : maximum_bytes_(maximum_bytes) {}
    [[nodiscard]] std::optional<NmeaFrame> push(char byte);
    void reset();

private:
    std::size_t maximum_bytes_;
    bool discarding_{false};
    std::string buffer_{};
};

struct CurrentFix {
    Position position{};
    UtcTime utc_time{};
    UtcDate utc_date{};
    std::uint8_t fix_quality{0};
    std::uint8_t satellites_used{0};
};

struct FixIngestResult {
    std::optional<CurrentFix> fix{};
    // True means the receiver explicitly reported no fix, or same-epoch
    // RMC/GGA data contradicted each other. Tracking candidates must be reset.
    bool invalid_fix{false};
};

// Requires matching, receiver-valid RMC and GGA reports. It prevents a valid
// status sentence from being combined with stale or contradictory position
// data from another epoch.
class FixAccumulator {
  public:
    [[nodiscard]] FixIngestResult ingest(const NmeaSentence& sentence);
    void clear();

  private:
    void clear_pending();
    std::optional<NmeaSentence> latest_rmc_{};
    std::optional<NmeaSentence> latest_gga_{};
    std::optional<CurrentFix> last_emitted_fix_{};
};

}  // namespace locator
