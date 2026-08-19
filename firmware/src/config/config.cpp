// SPDX-License-Identifier: GPL-3.0-or-later
#include "pocket_locator/config/config.hpp"

#include <algorithm>
#include <array>
#include <cctype>
#include <limits>

namespace pocket_locator::config {
namespace {

constexpr std::uint32_t kMinTimeoutMs = 1'000;
constexpr std::uint32_t kMaxTimeoutMs = 600'000;
constexpr std::uint32_t kMinTrackingIntervalMs = 5'000;
constexpr std::uint32_t kMaxTrackingIntervalMs = 60'000;
constexpr std::size_t kMaxTimeZoneLength = 64;
constexpr std::size_t kMaxDisplayBlocks = 12;
constexpr std::size_t kMaxBlockValueLength = 16;
constexpr std::size_t kMaxZoneTransitions = 48;

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
    bytes.push_back(settings.clock_24h ? 1 : 0);
    bytes.push_back(settings.show_seconds ? 1 : 0);
    bytes.push_back(static_cast<char>(settings.date_format));
    append_u32(bytes, static_cast<std::uint32_t>(settings.bottom_blocks.size()));
    for (const auto& block : settings.bottom_blocks) {
        bytes.push_back(static_cast<char>(block.kind));
        append_u32(bytes, static_cast<std::uint32_t>(block.value.size()));
        bytes.append(block.value);
    }
    append_u32(bytes, static_cast<std::uint32_t>(settings.zone_table.zone_name.size()));
    bytes.append(settings.zone_table.zone_name);
    for (const auto value : {settings.zone_table.generated_at_epoch_seconds, settings.zone_table.expires_at_epoch_seconds}) {
        for (unsigned shift = 0; shift < 64; shift += 8) bytes.push_back(static_cast<char>((static_cast<std::uint64_t>(value) >> shift) & 0xffU));
    }
    append_u32(bytes, static_cast<std::uint32_t>(settings.zone_table.initial_offset_seconds));
    append_u32(bytes, static_cast<std::uint32_t>(settings.zone_table.initial_abbreviation.size()));
    bytes.append(settings.zone_table.initial_abbreviation);
    append_u32(bytes, static_cast<std::uint32_t>(settings.zone_table.transitions.size()));
    for (const auto& transition : settings.zone_table.transitions) {
        for (unsigned shift = 0; shift < 64; shift += 8) bytes.push_back(static_cast<char>((static_cast<std::uint64_t>(transition.utc_epoch_seconds) >> shift) & 0xffU));
        append_u32(bytes, static_cast<std::uint32_t>(transition.offset_seconds));
        append_u32(bytes, static_cast<std::uint32_t>(transition.abbreviation.size()));
        bytes.append(transition.abbreviation);
    }
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
            return !std::isalnum(value) && value != '/' && value != '_' && value != '+' && value != '-' && value != '.';
        })) {
        return ValidationError::InvalidTimeZone;
    }
    if (settings.zone_table.zone_name != settings.named_time_zone || settings.zone_table.transitions.size() > kMaxZoneTransitions ||
        time::validate(settings.zone_table) != time::ZoneTableError::None) {
        return ValidationError::InvalidZoneTable;
    }
    if (settings.bottom_blocks.empty() || settings.bottom_blocks.size() > kMaxDisplayBlocks) return ValidationError::InvalidDisplayLayout;
    std::size_t width = 0;
    for (const auto& block : settings.bottom_blocks) {
        if (block.value.size() > kMaxBlockValueLength) return ValidationError::InvalidDisplayLayout;
        const auto printable = std::all_of(block.value.begin(), block.value.end(), [](unsigned char c) { return c >= 0x20U && c <= 0x7eU; });
        if (!printable) return ValidationError::InvalidDisplayLayout;
        switch (block.kind) {
            case DisplayBlockKind::Battery: if (!block.value.empty()) return ValidationError::InvalidDisplayLayout; ++width; break;
            case DisplayBlockKind::Time: if (!block.value.empty()) return ValidationError::InvalidDisplayLayout; width += settings.clock_24h ? (settings.show_seconds ? 8U : 5U) : (settings.show_seconds ? 11U : 8U); break;
            case DisplayBlockKind::Date: if (!block.value.empty()) return ValidationError::InvalidDisplayLayout; width += settings.date_format == DateFormat::YyyyMmDd ? 10U : 5U; break;
            case DisplayBlockKind::Text: width += block.value.size(); break;
            case DisplayBlockKind::Space:
                if (block.value.empty() || !std::all_of(block.value.begin(), block.value.end(), [](char c) { return c == ' '; })) return ValidationError::InvalidDisplayLayout;
                width += block.value.size(); break;
            case DisplayBlockKind::Separator:
                if (block.value.size() != 1U || std::string_view(" |/-:.").find(block.value.front()) == std::string_view::npos) return ValidationError::InvalidDisplayLayout;
                ++width; break;
            default: return ValidationError::InvalidDisplayLayout;
        }
        if (width > 16U) return ValidationError::InvalidDisplayLayout;
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
