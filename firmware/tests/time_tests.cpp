// SPDX-License-Identifier: GPL-3.0-or-later
#include "test_common.hpp"

#include "pocket_locator/time/zone_table.hpp"

namespace {

using pocket_locator::time::OffsetTransition;
using pocket_locator::time::ZoneTable;
using pocket_locator::time::ZoneTableError;

ZoneTable sample_table() {
    return ZoneTable{
        "America/New_York",
        1'700'000'000,
        2'200'000'000,
        -5 * 3'600,
        "EST",
        {
            OffsetTransition{1'710'054'000, -4 * 3'600, "EDT"},
            OffsetTransition{1'730'613'600, -5 * 3'600, "EST"},
        },
    };
}

}  // namespace

TEST(zone_table_applies_forward_and_backward_transitions) {
    const ZoneTable table = sample_table();
    REQUIRE_EQ(pocket_locator::time::validate(table), ZoneTableError::None);
    REQUIRE_EQ(pocket_locator::time::offset_at(table, 1'710'053'999).offset_seconds, -5 * 3'600);
    REQUIRE_EQ(pocket_locator::time::offset_at(table, 1'710'054'000).offset_seconds, -4 * 3'600);
    REQUIRE_EQ(pocket_locator::time::offset_at(table, 1'730'613'600).offset_seconds, -5 * 3'600);
}

TEST(zone_table_supports_fixed_and_fractional_hour_offsets) {
    ZoneTable singapore{"Asia/Singapore", 1, 100, 8 * 3'600, "+08", {}};
    REQUIRE_EQ(pocket_locator::time::validate(singapore), ZoneTableError::None);
    REQUIRE_EQ(pocket_locator::time::offset_at(singapore, 50).offset_seconds, 8 * 3'600);

    ZoneTable kathmandu{"Asia/Kathmandu", 1, 100, 5 * 3'600 + 45 * 60, "+0545", {}};
    REQUIRE_EQ(pocket_locator::time::validate(kathmandu), ZoneTableError::None);
    REQUIRE_EQ(pocket_locator::time::offset_at(kathmandu, 50).offset_seconds, 20'700);
}

TEST(zone_table_expiry_retains_last_offset_and_requests_refresh) {
    const ZoneTable table = sample_table();
    const auto result = pocket_locator::time::offset_at(table, table.expires_at_epoch_seconds);
    REQUIRE_EQ(result.offset_seconds, -5 * 3'600);
    REQUIRE(result.refresh_required);
}

TEST(zone_table_rejects_unordered_or_expired_transitions) {
    ZoneTable table = sample_table();
    table.transitions[1].utc_epoch_seconds = table.transitions[0].utc_epoch_seconds;
    REQUIRE_EQ(pocket_locator::time::validate(table), ZoneTableError::UnorderedTransitions);

    table = sample_table();
    table.transitions.back().utc_epoch_seconds = table.expires_at_epoch_seconds;
    REQUIRE_EQ(pocket_locator::time::validate(table), ZoneTableError::TransitionOutsideLifetime);
}
