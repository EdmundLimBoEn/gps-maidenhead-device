// SPDX-License-Identifier: GPL-3.0-or-later
#include "pocket_locator/storage/flash_config_store.hpp"

#include <array>
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstring>

#include "hardware/flash.h"
#include "hardware/sync.h"
#include "pico/platform.h"

namespace pocket_locator::storage {
namespace {
constexpr std::uint32_t kMagic = 0x504c4346U;  // "PLCF"
constexpr std::uint32_t kCommitted = 0U;
constexpr std::uint32_t kUncommitted = 0xffffffffU;
constexpr std::size_t kSlotCount = 2;
constexpr std::uint32_t kReservedBytes = kSlotCount * FLASH_SECTOR_SIZE;
constexpr std::uint32_t kStorageOffset = PICO_FLASH_SIZE_BYTES - kReservedBytes;
constexpr std::size_t kMaxBlocks = 12;
constexpr std::size_t kMaxTransitions = 48;

struct PackedBlock {
    std::uint8_t kind{};
    std::uint8_t value_size{};
    std::array<char, 16> value{};
};

struct PackedTransition {
    std::int64_t utc_epoch_seconds{};
    std::int32_t offset_seconds{};
    std::uint8_t abbreviation_size{};
    std::array<char, 8> abbreviation{};
};

struct PackedRecord {
    std::uint32_t magic{kMagic};
    std::uint32_t sequence{};
    std::uint32_t committed{kUncommitted};
    std::uint32_t schema_version{};
    std::uint8_t gnss_mode{};
    std::uint8_t normal_brightness{};
    std::uint8_t dim_brightness{};
    std::uint8_t clock_24h{};
    std::uint8_t show_seconds{};
    std::uint8_t date_format{};
    std::uint8_t time_zone_size{};
    std::uint8_t bottom_block_count{};
    std::uint8_t initial_abbreviation_size{};
    std::uint8_t transition_count{};
    std::uint32_t tracking_render_interval_ms{};
    std::uint32_t acquisition_timeout_ms{};
    std::uint32_t dim_deadline_ms{};
    std::uint32_t shutdown_deadline_ms{};
    std::int64_t zone_generated_at_epoch_seconds{};
    std::int64_t zone_expires_at_epoch_seconds{};
    std::int32_t zone_initial_offset_seconds{};
    std::array<char, 64> time_zone{};
    std::array<char, 8> initial_abbreviation{};
    std::array<PackedBlock, kMaxBlocks> bottom_blocks{};
    std::array<PackedTransition, kMaxTransitions> transitions{};
    std::uint32_t settings_crc{};
};
static_assert(sizeof(PackedRecord) < FLASH_SECTOR_SIZE);

[[nodiscard]] const PackedRecord* record_at(std::size_t index) {
    return reinterpret_cast<const PackedRecord*>(XIP_BASE + kStorageOffset + index * FLASH_SECTOR_SIZE);
}

[[nodiscard]] bool is_after(std::uint32_t left, std::uint32_t right) {
    return static_cast<std::int32_t>(left - right) > 0;
}

[[nodiscard]] config::Settings unpack(const PackedRecord& record) {
    config::Settings settings{};
    settings.schema_version = record.schema_version;
    settings.gnss_mode = static_cast<app::GnssMode>(record.gnss_mode);
    settings.tracking_render_interval_ms = record.tracking_render_interval_ms;
    settings.acquisition_timeout_ms = record.acquisition_timeout_ms;
    settings.dim_deadline_ms = record.dim_deadline_ms;
    settings.shutdown_deadline_ms = record.shutdown_deadline_ms;
    settings.normal_brightness = record.normal_brightness;
    settings.dim_brightness = record.dim_brightness;
    settings.clock_24h = record.clock_24h != 0;
    settings.show_seconds = record.show_seconds != 0;
    settings.date_format = static_cast<config::DateFormat>(record.date_format);
    if (record.time_zone_size <= record.time_zone.size()) {
        settings.named_time_zone.assign(record.time_zone.data(), record.time_zone_size);
    }
    if (record.bottom_block_count <= record.bottom_blocks.size()) {
        settings.bottom_blocks.clear();
        settings.bottom_blocks.reserve(record.bottom_block_count);
        for (std::size_t i = 0; i < record.bottom_block_count; ++i) {
            const auto& packed = record.bottom_blocks[i];
            if (packed.value_size > packed.value.size()) return {};
            settings.bottom_blocks.push_back({static_cast<config::DisplayBlockKind>(packed.kind),
                                              std::string(packed.value.data(), packed.value_size)});
        }
    }
    settings.zone_table.zone_name = settings.named_time_zone;
    settings.zone_table.generated_at_epoch_seconds = record.zone_generated_at_epoch_seconds;
    settings.zone_table.expires_at_epoch_seconds = record.zone_expires_at_epoch_seconds;
    settings.zone_table.initial_offset_seconds = record.zone_initial_offset_seconds;
    if (record.initial_abbreviation_size <= record.initial_abbreviation.size()) {
        settings.zone_table.initial_abbreviation.assign(record.initial_abbreviation.data(), record.initial_abbreviation_size);
    }
    if (record.transition_count <= record.transitions.size()) {
        settings.zone_table.transitions.clear();
        settings.zone_table.transitions.reserve(record.transition_count);
        for (std::size_t i = 0; i < record.transition_count; ++i) {
            const auto& packed = record.transitions[i];
            if (packed.abbreviation_size > packed.abbreviation.size()) return {};
            settings.zone_table.transitions.push_back({packed.utc_epoch_seconds, packed.offset_seconds,
                                                       std::string(packed.abbreviation.data(), packed.abbreviation_size)});
        }
    }
    return settings;
}

[[nodiscard]] bool payload_valid(const PackedRecord& record) {
    if (record.magic != kMagic || record.time_zone_size > record.time_zone.size() ||
        record.bottom_block_count > record.bottom_blocks.size() || record.initial_abbreviation_size > record.initial_abbreviation.size() ||
        record.transition_count > record.transitions.size()) {
        return false;
    }
    const auto settings = unpack(record);
    return config::validate(settings) == config::ValidationError::None && record.settings_crc == config::crc32(settings);
}

[[nodiscard]] bool valid(const PackedRecord& record) {
    return record.committed == kCommitted && payload_valid(record);
}

[[nodiscard]] int newest_valid_slot() {
    const bool first = valid(*record_at(0));
    const bool second = valid(*record_at(1));
    if (!first && !second) return -1;
    if (!first) return 1;
    if (!second) return 0;
    return is_after(record_at(1)->sequence, record_at(0)->sequence) ? 1 : 0;
}

[[nodiscard]] PackedRecord pack(const config::Settings& settings, std::uint32_t sequence) {
    PackedRecord record{};
    record.sequence = sequence;
    record.schema_version = settings.schema_version;
    record.gnss_mode = static_cast<std::uint8_t>(settings.gnss_mode);
    record.normal_brightness = settings.normal_brightness;
    record.dim_brightness = settings.dim_brightness;
    record.clock_24h = settings.clock_24h ? 1U : 0U;
    record.show_seconds = settings.show_seconds ? 1U : 0U;
    record.date_format = static_cast<std::uint8_t>(settings.date_format);
    record.time_zone_size = static_cast<std::uint8_t>(settings.named_time_zone.size());
    record.bottom_block_count = static_cast<std::uint8_t>(settings.bottom_blocks.size());
    record.initial_abbreviation_size = static_cast<std::uint8_t>(settings.zone_table.initial_abbreviation.size());
    record.transition_count = static_cast<std::uint8_t>(settings.zone_table.transitions.size());
    record.tracking_render_interval_ms = settings.tracking_render_interval_ms;
    record.acquisition_timeout_ms = settings.acquisition_timeout_ms;
    record.dim_deadline_ms = settings.dim_deadline_ms;
    record.shutdown_deadline_ms = settings.shutdown_deadline_ms;
    std::memcpy(record.time_zone.data(), settings.named_time_zone.data(), settings.named_time_zone.size());
    record.zone_generated_at_epoch_seconds = settings.zone_table.generated_at_epoch_seconds;
    record.zone_expires_at_epoch_seconds = settings.zone_table.expires_at_epoch_seconds;
    record.zone_initial_offset_seconds = settings.zone_table.initial_offset_seconds;
    std::memcpy(record.initial_abbreviation.data(), settings.zone_table.initial_abbreviation.data(), settings.zone_table.initial_abbreviation.size());
    for (std::size_t i = 0; i < settings.bottom_blocks.size(); ++i) {
        const auto& input = settings.bottom_blocks[i];
        auto& output = record.bottom_blocks[i];
        output.kind = static_cast<std::uint8_t>(input.kind);
        output.value_size = static_cast<std::uint8_t>(input.value.size());
        std::memcpy(output.value.data(), input.value.data(), input.value.size());
    }
    for (std::size_t i = 0; i < settings.zone_table.transitions.size(); ++i) {
        const auto& input = settings.zone_table.transitions[i];
        auto& output = record.transitions[i];
        output.utc_epoch_seconds = input.utc_epoch_seconds;
        output.offset_seconds = input.offset_seconds;
        output.abbreviation_size = static_cast<std::uint8_t>(input.abbreviation.size());
        std::memcpy(output.abbreviation.data(), input.abbreviation.data(), input.abbreviation.size());
    }
    record.settings_crc = config::crc32(settings);
    return record;
}

void program_page(std::uint32_t offset, const void* page) {
    const auto interrupts = save_and_disable_interrupts();
    flash_range_program(offset, static_cast<const std::uint8_t*>(page), FLASH_PAGE_SIZE);
    restore_interrupts(interrupts);
}

void program_record(std::uint32_t offset, const PackedRecord& record) {
    std::array<std::uint8_t, FLASH_PAGE_SIZE> page{};
    const auto* bytes = reinterpret_cast<const std::uint8_t*>(&record);
    for (std::size_t written = 0; written < sizeof(record); written += FLASH_PAGE_SIZE) {
        page.fill(0xffU);
        const std::size_t count = std::min<std::size_t>(FLASH_PAGE_SIZE, sizeof(record) - written);
        std::memcpy(page.data(), bytes + written, count);
        program_page(offset + static_cast<std::uint32_t>(written), page.data());
    }
}

}  // namespace

config::LoadResult FlashConfigStore::load() const {
    const int selected = newest_valid_slot();
    if (selected < 0) return {config::factory_defaults(), true, false, -1};
    return {unpack(*record_at(static_cast<std::size_t>(selected))), false, true, selected};
}

config::ValidationError FlashConfigStore::write(const config::Settings& settings) {
    if (const auto validation = config::validate(settings); validation != config::ValidationError::None) return validation;
    const int active = newest_valid_slot();
    const std::size_t target = active == 0 ? 1U : 0U;
    const auto record = pack(settings, active < 0 ? 1U : record_at(static_cast<std::size_t>(active))->sequence + 1U);
    const std::uint32_t offset = kStorageOffset + static_cast<std::uint32_t>(target * FLASH_SECTOR_SIZE);

    const auto interrupts = save_and_disable_interrupts();
    flash_range_erase(offset, FLASH_SECTOR_SIZE);
    restore_interrupts(interrupts);

    program_record(offset, record);
    if (!payload_valid(*record_at(target)) || record_at(target)->committed != kUncommitted) return config::ValidationError::UnsupportedSchema;

    // NOR flash can only change one bits to zero. Reprogramming this page with
    // FF everywhere except the commit marker preserves the verified payload.
    std::array<std::uint8_t, FLASH_PAGE_SIZE> page{};
    page.fill(0xffU);
    const std::size_t marker = offsetof(PackedRecord, committed);
    std::memset(page.data() + marker, 0, sizeof(kCommitted));
    program_page(offset, page.data());
    return valid(*record_at(target)) ? config::ValidationError::None : config::ValidationError::UnsupportedSchema;
}

config::ValidationError FlashConfigStore::factory_reset() {
    const auto interrupts = save_and_disable_interrupts();
    flash_range_erase(kStorageOffset, kReservedBytes);
    restore_interrupts(interrupts);
    return config::ValidationError::None;
}

}  // namespace pocket_locator::storage
