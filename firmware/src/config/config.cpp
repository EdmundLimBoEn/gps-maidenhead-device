// SPDX-License-Identifier: GPL-3.0-or-later
#include "pocket_locator/config/config.hpp"

#include <algorithm>
#include <array>
#include <limits>

namespace pocket_locator::config {
namespace {

constexpr std::uint32_t kMinTimeoutMs = 1'000;
constexpr std::uint32_t kMaxTimeoutMs = 600'000;
constexpr std::uint32_t kMinTrackingIntervalMs = 1'000;
constexpr std::uint32_t kMaxTrackingIntervalMs = 60'000;
constexpr std::size_t kMaxTimeZoneLength = 64;

void append_u32(std::string& bytes, std::uint32_t value) {
    for (unsigned shift = 0; shift < 32; shift += 8) {
        bytes.push_back(static_cast<char>((value >> shift) & 0xffU));
    }
}

std::string serialized(const Settings& settings) {
    std::string bytes;
    bytes.reserve(32 + settings.named_time_zone.size());
    append_u32(bytes, settings.schema_version);
    bytes.push_back(static_cast<char>(settings.gnss_mode));
    append_u32(bytes, settings.tracking_render_interval_ms);
    append_u32(bytes, settings.acquisition_timeout_ms);
    append_u32(bytes, settings.dim_deadline_ms);
    append_u32(bytes, settings.shutdown_deadline_ms);
    bytes.push_back(static_cast<char>(settings.normal_brightness));
    bytes.push_back(static_cast<char>(settings.dim_brightness));
    append_u32(bytes, static_cast<std::uint32_t>(settings.named_time_zone.size()));
    bytes.append(settings.named_time_zone);
    return bytes;
}

}  // namespace

Settings factory_defaults() {
    return {};
}

ValidationError validate(const Settings& settings) {
    if (settings.schema_version != kCurrentSchemaVersion) {
        return ValidationError::UnsupportedSchema;
    }
    if (settings.gnss_mode != app::GnssMode::SingleFix && settings.gnss_mode != app::GnssMode::Tracking) {
        return ValidationError::InvalidGnssMode;
    }
    if (settings.tracking_render_interval_ms < kMinTrackingIntervalMs ||
        settings.tracking_render_interval_ms > kMaxTrackingIntervalMs) {
        return ValidationError::InvalidTrackingInterval;
    }
    if (settings.acquisition_timeout_ms < kMinTimeoutMs || settings.acquisition_timeout_ms > kMaxTimeoutMs) {
        return ValidationError::InvalidAcquisitionTimeout;
    }
    if (settings.dim_deadline_ms > settings.shutdown_deadline_ms ||
        settings.acquisition_timeout_ms > settings.shutdown_deadline_ms ||
        settings.shutdown_deadline_ms < kMinTimeoutMs || settings.shutdown_deadline_ms > kMaxTimeoutMs) {
        return ValidationError::InvalidDeadlineOrder;
    }
    if (settings.normal_brightness > 100 || settings.dim_brightness > settings.normal_brightness) {
        return ValidationError::InvalidBrightness;
    }
    if (settings.named_time_zone.empty() || settings.named_time_zone.size() > kMaxTimeZoneLength ||
        std::any_of(settings.named_time_zone.begin(), settings.named_time_zone.end(), [](unsigned char value) {
            return value < 0x20U || value > 0x7eU;
        })) {
        return ValidationError::InvalidTimeZone;
    }
    return ValidationError::None;
}

std::uint32_t crc32(const Settings& settings) {
    const std::string bytes = serialized(settings);
    std::uint32_t crc = 0xffffffffU;
    for (unsigned char byte : bytes) {
        crc ^= byte;
        for (int bit = 0; bit < 8; ++bit) {
            crc = (crc & 1U) != 0U ? (crc >> 1U) ^ 0xedb88320U : crc >> 1U;
        }
    }
    return ~crc;
}

bool TwoSlotStore::slot_is_valid(const Slot& slot) {
    return slot.current_marker && validate(slot.settings) == ValidationError::None && slot.stored_crc == crc32(slot.settings);
}

bool TwoSlotStore::sequence_after(std::uint32_t lhs, std::uint32_t rhs) {
    return static_cast<std::int32_t>(lhs - rhs) > 0;
}

int TwoSlotStore::newest_valid_slot() const {
    const bool first_valid = slot_is_valid(slots_[0]);
    const bool second_valid = slot_is_valid(slots_[1]);
    if (!first_valid && !second_valid) {
        return -1;
    }
    if (!first_valid) {
        return 1;
    }
    if (!second_valid) {
        return 0;
    }
    return sequence_after(slots_[1].sequence, slots_[0].sequence) ? 1 : 0;
}

LoadResult TwoSlotStore::load() const {
    const int selected = newest_valid_slot();
    if (selected < 0) {
        return {factory_defaults(), true, false, -1};
    }
    return {slots_[static_cast<std::size_t>(selected)].settings, false, true, selected};
}

ValidationError TwoSlotStore::write(const Settings& settings, WriteInterruption interruption) {
    const ValidationError validation = validate(settings);
    if (validation != ValidationError::None) {
        return validation;
    }
    if (interruption == WriteInterruption::BeforePayload) {
        return ValidationError::None;
    }

    const int active = newest_valid_slot();
    const std::size_t target = active == 0 ? 1U : 0U;
    Slot staged{};
    staged.sequence = active < 0 ? 1U : slots_[static_cast<std::size_t>(active)].sequence + 1U;
    staged.settings = settings;
    slots_[target] = staged;
    if (interruption == WriteInterruption::AfterPayload) {
        return ValidationError::None;
    }

    slots_[target].stored_crc = crc32(settings);
    if (interruption == WriteInterruption::AfterVerification) {
        return ValidationError::None;
    }

    slots_[target].current_marker = true;
    return ValidationError::None;
}

void TwoSlotStore::corrupt_crc_for_test(std::size_t slot_index) {
    slots_.at(slot_index).stored_crc ^= 0x00000001U;
}

const Slot& TwoSlotStore::slot_for_test(std::size_t slot_index) const {
    return slots_.at(slot_index);
}

}  // namespace pocket_locator::config
