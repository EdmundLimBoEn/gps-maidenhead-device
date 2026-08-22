// SPDX-License-Identifier: GPL-3.0-or-later
#include "test_common.hpp"

#include "pocket_locator/display/format.hpp"

TEST(display_expands_custom_blocks_with_zone_transition_offset) {
    auto settings = pocket_locator::config::factory_defaults();
    settings.clock_24h = false;
    settings.show_seconds = true;
    settings.date_format = pocket_locator::config::DateFormat::DdMmm;
    settings.bottom_blocks = {
        {pocket_locator::config::DisplayBlockKind::Battery, ""},
        {pocket_locator::config::DisplayBlockKind::Space, " "},
        {pocket_locator::config::DisplayBlockKind::Time, ""},
    };
    locator::CurrentFix fix{{1.0, 2.0}, {16, 59, 58, 0}, {2026, 1, 1}};
    const auto screen = pocket_locator::display::format_fix_screen(settings, "OJ11XH", fix, 80, false);

    REQUIRE_EQ(screen.top_row, std::string("GRID: OJ11XH"));
    REQUIRE_EQ(screen.bottom_row, std::string("\x03 12:59:58 AM"));
    REQUIRE(!screen.timezone_refresh_required);
}

TEST(display_reports_expired_zone_table_but_keeps_last_known_offset) {
    auto settings = pocket_locator::config::factory_defaults();
    settings.bottom_blocks = {{pocket_locator::config::DisplayBlockKind::Time, ""}};
    settings.zone_table.generated_at_epoch_seconds = 0;
    settings.zone_table.expires_at_epoch_seconds = 1;
    locator::CurrentFix fix{{1.0, 2.0}, {0, 0, 0, 0}, {2026, 1, 1}};
    const auto screen = pocket_locator::display::format_fix_screen(settings, "OJ11XH", fix, 80, false);

    REQUIRE_EQ(screen.bottom_row, std::string("08:00"));
    REQUIRE(screen.timezone_refresh_required);
}

TEST(display_clock_advances_from_last_live_gnss_fix) {
    auto settings = pocket_locator::config::factory_defaults();
    settings.bottom_blocks = {{pocket_locator::config::DisplayBlockKind::Time, ""}};
    locator::CurrentFix fix{{1.0, 2.0}, {15, 59, 30, 0}, {2026, 1, 1}};
    const auto screen = pocket_locator::display::format_fix_screen(
        settings, "OJ11XH", fix, 80, false, 90);

    REQUIRE_EQ(screen.bottom_row, std::string("00:01"));
}
