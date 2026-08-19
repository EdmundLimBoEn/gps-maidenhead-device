// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string>

#include "pocket_locator/app/check_session.hpp"

namespace pocket_locator::config {

constexpr std::uint32_t kCurrentSchemaVersion = 1;

struct Settings {
    std::uint32_t schema_version{kCurrentSchemaVersion};
    app::GnssMode gnss_mode{app::GnssMode::SingleFix};
    std::uint32_t tracking_render_interval_ms{5'000};
    std::uint32_t acquisition_timeout_ms{120'000};
    std::uint32_t dim_deadline_ms{60'000};
    std::uint32_t shutdown_deadline_ms{120'000};
    std::uint8_t normal_brightness{100};
    std::uint8_t dim_brightness{20};
    std::string named_time_zone{"Asia/Singapore"};
};

[[nodiscard]] Settings factory_defaults();

enum class ValidationError {
    None,
    UnsupportedSchema,
    InvalidGnssMode,
    InvalidTrackingInterval,
    InvalidAcquisitionTimeout,
    InvalidDeadlineOrder,
    InvalidBrightness,
    InvalidTimeZone,
};

[[nodiscard]] ValidationError validate(const Settings& settings);
[[nodiscard]] std::uint32_t crc32(const Settings& settings);

enum class WriteInterruption {
    None,
    BeforePayload,
    AfterPayload,
    AfterVerification,
};

struct Slot {
    bool current_marker{false};
    std::uint32_t sequence{0};
    Settings settings{};
    std::uint32_t stored_crc{0};
};

struct LoadResult {
    Settings settings{};
    bool used_factory_defaults{true};
    bool crc_healthy{false};
    int selected_slot{-1};
};

// In-memory model of the two flash records.  It deliberately preserves the
// older record until the new record has been verified and marked current.
class TwoSlotStore {
public:
    [[nodiscard]] LoadResult load() const;
    [[nodiscard]] ValidationError write(
        const Settings& settings,
        WriteInterruption interruption = WriteInterruption::None);

    void corrupt_crc_for_test(std::size_t slot_index);
    [[nodiscard]] const Slot& slot_for_test(std::size_t slot_index) const;

private:
    [[nodiscard]] static bool slot_is_valid(const Slot& slot);
    [[nodiscard]] static bool sequence_after(std::uint32_t lhs, std::uint32_t rhs);
    [[nodiscard]] int newest_valid_slot() const;

    std::array<Slot, 2> slots_{};
};

}  // namespace pocket_locator::config
