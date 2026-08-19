// SPDX-License-Identifier: GPL-3.0-or-later
#include "pocket_locator/time/zone_table.hpp"

#include <algorithm>

namespace pocket_locator::time {
namespace {

constexpr std::int32_t kMaximumOffsetSeconds = 24 * 60 * 60;
constexpr std::size_t kMaximumZoneNameBytes = 64;
constexpr std::size_t kMaximumAbbreviationBytes = 8;

bool printable_ascii(const std::string& value) {
    return std::all_of(value.begin(), value.end(), [](const unsigned char character) {
        return character >= 0x20U && character <= 0x7eU;
    });
}

bool valid_abbreviation(const std::string& value) {
    return !value.empty() && value.size() <= kMaximumAbbreviationBytes && printable_ascii(value);
}

}  // namespace

ZoneTableError validate(const ZoneTable& table) {
    if (table.zone_name.empty() || table.zone_name.size() > kMaximumZoneNameBytes ||
        !printable_ascii(table.zone_name)) {
        return ZoneTableError::InvalidName;
    }
    if (table.expires_at_epoch_seconds <= table.generated_at_epoch_seconds) {
        return ZoneTableError::InvalidLifetime;
    }
    if (table.initial_offset_seconds < -kMaximumOffsetSeconds ||
        table.initial_offset_seconds > kMaximumOffsetSeconds) {
        return ZoneTableError::InvalidOffset;
    }
    if (!valid_abbreviation(table.initial_abbreviation)) {
        return ZoneTableError::InvalidAbbreviation;
    }
    std::int64_t previous = table.generated_at_epoch_seconds;
    for (const auto& transition : table.transitions) {
        if (transition.utc_epoch_seconds <= previous) {
            return ZoneTableError::UnorderedTransitions;
        }
        if (transition.utc_epoch_seconds >= table.expires_at_epoch_seconds) {
            return ZoneTableError::TransitionOutsideLifetime;
        }
        if (transition.offset_seconds < -kMaximumOffsetSeconds ||
            transition.offset_seconds > kMaximumOffsetSeconds) {
            return ZoneTableError::InvalidOffset;
        }
        if (!valid_abbreviation(transition.abbreviation)) {
            return ZoneTableError::InvalidAbbreviation;
        }
        previous = transition.utc_epoch_seconds;
    }
    return ZoneTableError::None;
}

OffsetAtResult offset_at(const ZoneTable& table, std::int64_t utc_epoch_seconds) {
    OffsetAtResult result{table.initial_offset_seconds, table.initial_abbreviation,
                          utc_epoch_seconds >= table.expires_at_epoch_seconds};
    for (const auto& transition : table.transitions) {
        if (transition.utc_epoch_seconds > utc_epoch_seconds) {
            break;
        }
        result.offset_seconds = transition.offset_seconds;
        result.abbreviation = transition.abbreviation;
    }
    return result;
}

}  // namespace pocket_locator::time
