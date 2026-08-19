// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace pocket_locator::time {

struct OffsetTransition {
    std::int64_t utc_epoch_seconds{0};
    std::int32_t offset_seconds{0};
    std::string abbreviation;
};

struct ZoneTable {
    std::string zone_name{"Asia/Singapore"};
    std::int64_t generated_at_epoch_seconds{0};
    std::int64_t expires_at_epoch_seconds{0};
    std::int32_t initial_offset_seconds{8 * 60 * 60};
    std::string initial_abbreviation{"+08"};
    std::vector<OffsetTransition> transitions;
};

enum class ZoneTableError {
    None,
    InvalidName,
    InvalidLifetime,
    InvalidOffset,
    InvalidAbbreviation,
    UnorderedTransitions,
    TransitionOutsideLifetime,
};

struct OffsetAtResult {
    std::int32_t offset_seconds{0};
    std::string abbreviation;
    bool refresh_required{false};
};

[[nodiscard]] ZoneTableError validate(const ZoneTable& table);

// After expiry the final known offset remains usable, but diagnostics must
// expose refresh_required until the host sends a regenerated table.
[[nodiscard]] OffsetAtResult offset_at(const ZoneTable& table, std::int64_t utc_epoch_seconds);

}  // namespace pocket_locator::time
